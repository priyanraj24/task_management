from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.projects import service
from app.projects.schemas import VALID_PROJECT_STATUSES
from app.tasks import service as task_service
from app.users import service as user_service


def _get_scoped_query(db: Session, current_user):
    if current_user.role == "manager":
        return service.get_by_manager(db, current_user.id)
    elif current_user.role == "employee":
        assigned_project_ids = task_service.get_assigned_project_ids(db, current_user.id)
        return service.get_by_ids(db, assigned_project_ids)
    return service.get_all(db)


def create_project(db: Session, data: dict, current_user):
    if data["end_date"] < data["start_date"]:
        raise HTTPException(status_code=400, detail="End date cannot be before start date")

    if service.find_by_name(db, data["name"]):
        raise HTTPException(status_code=409, detail="Project with this name already exists")

    try:
        service.create(db, **data, created_by=current_user.id)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Project with this name already exists")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create project")

    return [p.to_dict() for p in _get_scoped_query(db, current_user).all()]


def get_projects(db: Session, current_user, search: str, status: str, page: int, limit: int):
    if status and status not in VALID_PROJECT_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(VALID_PROJECT_STATUSES)}")

    query = _get_scoped_query(db, current_user)
    from app.database import paginate
    query = service.filter_projects(query, search, status)
    projects, total = paginate(query, page, limit)
    return {
        "list": [p.to_dict() for p in projects],
        "total": total,
        "page": page,
        "limit": limit,
    }


def get_project(db: Session, project_id: int, current_user):
    project = service.find_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    _check_project_access(db, project, current_user)

    return project.to_dict()


def update_project(db: Session, project_id: int, data: dict, current_user):
    project = service.find_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role == "manager" and project.assigned_to != current_user.id and project.created_by != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    if "name" in data and data["name"] != project.name:
        if service.find_by_name(db, data["name"]):
            raise HTTPException(status_code=409, detail="Project with this name already exists")

    start = data.get("start_date", project.start_date)
    end = data.get("end_date", project.end_date)
    if start and end and end < start:
        raise HTTPException(status_code=400, detail="End date cannot be before start date")

    data.pop("assigned_to", None)

    try:
        return service.update(db, project, data).to_dict()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Project with this name already exists")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update project")


def delete_project(db: Session, project_id: int, current_user):
    project = service.find_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        service.soft_delete(db, project)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete project")

    return [p.to_dict() for p in _get_scoped_query(db, current_user).all()]


def get_project_tasks(db: Session, project_id: int, current_user):
    project = service.find_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    _check_project_access(db, project, current_user)

    tasks = task_service.get_by_project_id(db, project_id)
    return [t.to_dict() for t in tasks]


def assign_project(db: Session, project_id: int, user_id: int, current_user):
    project = service.find_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot assign project to yourself")

    user = user_service.find_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=400, detail="User does not exist")

    if user.role != "manager":
        raise HTTPException(status_code=400, detail="Project can only be assigned to a manager")

    if project.assigned_to == user_id:
        raise HTTPException(status_code=400, detail="Project is already assigned to this manager")

    try:
        return service.update(db, project, {"assigned_to": user_id}).to_dict()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to assign project")


def _check_project_access(db: Session, project, current_user):
    if current_user.role == "manager" and project.assigned_to != current_user.id and project.created_by != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role == "employee":
        if not task_service.has_assigned_task(db, project.id, current_user.id):
            raise HTTPException(status_code=404, detail="Project not found")
