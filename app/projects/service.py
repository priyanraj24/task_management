from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.projects.models import Project, ProjectUser
from app.projects.schemas import VALID_PROJECT_STATUSES
from app.tasks.models import Task, TaskAssignment, Attachment
from app.users import service as user_service


UPDATABLE_FIELDS = {"name", "description", "status", "start_date", "end_date"}


def find_by_id(db: Session, project_id: int):
    return db.query(Project).filter(Project.id == project_id, Project.is_deleted == False).first()


def find_by_name(db: Session, name: str):
    return db.query(Project).filter(Project.name == name, Project.is_deleted == False).first()


def get_all(db: Session):
    return db.query(Project).filter(Project.is_deleted == False).order_by(Project.created_at.desc())


def get_by_user(db: Session, user_id: int):
    return (
        db.query(Project)
        .join(ProjectUser, (ProjectUser.project_id == Project.id) & (ProjectUser.is_deleted == False))
        .filter(ProjectUser.user_id == user_id, Project.is_deleted == False)
        .order_by(Project.created_at.desc())
        .distinct()
    )


def filter_projects(query, search: str, status: str):
    if search:
        query = query.filter(Project.name.ilike(f"%{search}%"))
    if status:
        query = query.filter(Project.status == status)
    return query


def check_project_access(project, current_user):
    if current_user.role in ("manager", "employee") and current_user.id not in project.assignee_ids:
        raise HTTPException(status_code=404, detail="Project not found")


def check_manager_project_access(project, current_user):
    if current_user.role == "manager" and current_user.id not in project.assignee_ids:
        raise HTTPException(status_code=404, detail="Project not found")


def create_project(db: Session, data: dict, current_user, page: int = 1, limit: int = 10):
    if data["end_date"] < data["start_date"]:
        raise HTTPException(status_code=400, detail="End date cannot be before start date")

    if find_by_name(db, data["name"]):
        raise HTTPException(status_code=409, detail="Project with this name already exists")

    try:
        project = Project(**data, created_by=current_user.id)
        db.add(project)
        db.flush()
        if current_user.role == "manager":
            db.add(ProjectUser(project_id=project.id, user_id=current_user.id, assigned_by=current_user.id))
        db.commit()
        db.refresh(project)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Project with this name already exists")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create project")

    return get_projects(db, current_user, name="", status="", page=page, limit=limit)


def get_projects(db: Session, current_user, name: str, status: str, page: int, limit: int):
    if status and status not in VALID_PROJECT_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(VALID_PROJECT_STATUSES)}")

    conditions = ["p.is_deleted = false"]
    params = {"limit": limit, "offset": (page - 1) * limit}

    if current_user.role in ("manager", "employee"):
        conditions.append(
            "EXISTS (SELECT 1 FROM project_users pu2 WHERE pu2.project_id = p.id AND pu2.user_id = :user_id AND pu2.is_deleted = false)"
        )
        params["user_id"] = current_user.id

    if name:
        conditions.append("p.name ILIKE :name")
        params["name"] = f"%{name}%"
    if status:
        conditions.append("p.status = :status")
        params["status"] = status

    where = " AND ".join(conditions)

    sql = f"""
        WITH filtered_projects AS (
            SELECT p.id, p.name, p.description, p.status,
                   p.start_date, p.end_date, p.created_by, p.created_at
            FROM projects p
            WHERE {where}
        ),
        total_count AS (
            SELECT COUNT(*) AS total FROM filtered_projects
        ),
        paginated_projects AS (
            SELECT * FROM filtered_projects
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        ),
        project_data AS (
            SELECT
                pp.id, pp.name, pp.description, pp.status,
                pp.start_date, pp.end_date, pp.created_by, pp.created_at,
                u.id AS assignee_id, u.name AS assignee_name, u.role AS assignee_role
            FROM paginated_projects pp
            LEFT JOIN project_users pu ON pu.project_id = pp.id AND pu.is_deleted = false
            LEFT JOIN users u ON u.id = pu.user_id AND u.is_deleted = false
        )
        SELECT
            (SELECT total FROM total_count) AS total,
            COALESCE(json_agg(
                json_build_object(
                    'id', pd.id,
                    'name', pd.name,
                    'description', pd.description,
                    'status', pd.status,
                    'start_date', pd.start_date,
                    'end_date', pd.end_date,
                    'created_by', pd.created_by,
                    'created_at', pd.created_at,
                    'assigned_to', pd.assignees
                )
            ), '[]'::json) AS list
        FROM (
            SELECT
                pd.id, pd.name, pd.description, pd.status,
                pd.start_date, pd.end_date, pd.created_by, pd.created_at,
                COALESCE(
                    json_agg(json_build_object('id', pd.assignee_id, 'name', pd.assignee_name, 'role', pd.assignee_role))
                    FILTER (WHERE pd.assignee_id IS NOT NULL),
                    '[]'::json
                ) AS assignees
            FROM project_data pd
            GROUP BY pd.id, pd.name, pd.description, pd.status, pd.start_date, pd.end_date, pd.created_by, pd.created_at
            ORDER BY pd.created_at DESC
        ) pd
    """

    row = db.execute(text(sql), params).mappings().one()
    return {
        "list": row["list"],
        "total": row["total"],
        "page": page,
        "limit": limit,
    }


def get_project(db: Session, project_id: int, current_user):
    project = find_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    check_project_access(project, current_user)
    return project.to_dict()


def update_project(db: Session, project_id: int, data: dict, current_user):
    project = find_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    check_manager_project_access(project, current_user)

    if "name" in data and data["name"] != project.name:
        if find_by_name(db, data["name"]):
            raise HTTPException(status_code=409, detail="Project with this name already exists")

    start = data.get("start_date", project.start_date)
    end = data.get("end_date", project.end_date)
    if start and end and end < start:
        raise HTTPException(status_code=400, detail="End date cannot be before start date")

    data.pop("assigned_to", None)

    try:
        for key, value in data.items():
            if key in UPDATABLE_FIELDS:
                setattr(project, key, value)
        db.commit()
        db.refresh(project)
        return project.to_dict()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Project with this name already exists")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update project")


def delete_project(db: Session, project_id: int, current_user, page: int = 1, limit: int = 10):
    project = find_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:

        project_assignments = db.query(ProjectUser).filter(ProjectUser.project_id == project.id, ProjectUser.is_deleted == False).all()
        for pa in project_assignments:
            pa.soft_delete()
        tasks = db.query(Task).filter(Task.project_id == project.id, Task.is_deleted == False).all()
        for task in tasks:
            task_assignments = db.query(TaskAssignment).filter(TaskAssignment.task_id == task.id, TaskAssignment.is_deleted == False).all()
            for ta in task_assignments:
                ta.soft_delete()
            attachments = db.query(Attachment).filter(Attachment.task_id == task.id, Attachment.is_deleted == False).all()
            for att in attachments:
                att.soft_delete()
            task.soft_delete()
        project.soft_delete()
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete project")

    return get_projects(db, current_user, name="", status="", page=page, limit=limit)


def get_project_tasks(db: Session, project_id: int, current_user, page: int = 1, limit: int = 10):
    project = find_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    check_project_access(project, current_user)

    from app.tasks import service as task_service
    return task_service.get_tasks(db, current_user, title="", project_id=project_id, employee_id=None, status="", priority="", page=page, limit=limit)


def assign_project(db: Session, project_id: int, user_id: int, current_user):
    project = find_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    check_manager_project_access(project, current_user)

    if project.status in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail="Cannot assign project when project is completed or cancelled")

    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot assign project to yourself")


    user = user_service.find_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=400, detail="User does not exist")

    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Cannot assign project to an admin")

    if current_user.role == "manager" and user.role != "employee":
        raise HTTPException(status_code=400, detail="Managers can only assign employees to a project")

    if user_id in project.assignee_ids:
        raise HTTPException(status_code=400, detail="User is already assigned to this project")

    try:
        existing = (
            db.query(ProjectUser)
            .filter(ProjectUser.project_id == project_id, ProjectUser.user_id == user_id, ProjectUser.is_deleted == True)
            .first()
        )
        if existing:
            existing.is_deleted = False
            existing.deleted_at = None
            existing.assigned_by = current_user.id
        else:
            db.add(ProjectUser(project_id=project_id, user_id=user_id, assigned_by=current_user.id))
        db.commit()
        db.refresh(project)
        return project.to_dict()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to assign project")


def unassign_project(db: Session, project_id: int, user_id: int, current_user):
    project = find_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    check_manager_project_access(project, current_user)


    user = user_service.find_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=400, detail="User does not exist")

    if current_user.role == "manager" and user.role != "employee":
        raise HTTPException(status_code=400, detail="Managers can only unassign employees from a project")

    assignment = (
        db.query(ProjectUser)
        .filter(ProjectUser.project_id == project_id, ProjectUser.user_id == user_id, ProjectUser.is_deleted == False)
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=400, detail="User is not assigned to this project")

    try:
        assignment.soft_delete()

        if user.role == "employee":

            task_ids = db.query(Task.id).filter(Task.project_id == project_id, Task.is_deleted == False).subquery()
            task_assignments = (
                db.query(TaskAssignment)
                .filter(
                    TaskAssignment.task_id.in_(task_ids),
                    TaskAssignment.user_id == user_id,
                    TaskAssignment.is_deleted == False,
                )
                .all()
            )
            for ta in task_assignments:
                ta.soft_delete()

        db.commit()
        db.refresh(project)
        return project.to_dict()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to unassign project")
