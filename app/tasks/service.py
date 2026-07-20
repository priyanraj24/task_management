import os
import uuid
from datetime import date

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.tasks.models import Task, TaskAssignment, TaskHistory, Attachment
from app.tasks.schemas import VALID_STATUSES, VALID_PRIORITIES
from app.users import service as user_service


UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt"}

UPDATABLE_FIELDS = {"title", "description", "status", "priority", "due_date"}


# --- Query helpers ---

def find_task_by_id(db: Session, task_id: int):
    return db.query(Task).filter(Task.id == task_id, Task.is_deleted == False).first()


def get_all(db: Session):
    return db.query(Task).filter(Task.is_deleted == False).order_by(Task.created_at.desc())


def get_by_assignee(db: Session, user_id: int):
    return (
        db.query(Task)
        .join(TaskAssignment)
        .filter(TaskAssignment.user_id == user_id, TaskAssignment.is_deleted == False, Task.is_deleted == False)
        .order_by(Task.created_at.desc())
        .distinct()
    )


def get_by_project_id(db: Session, project_id: int):
    return db.query(Task).filter(Task.project_id == project_id, Task.is_deleted == False).order_by(Task.created_at.desc()).all()


def get_by_project_ids(db: Session, project_ids):
    return db.query(Task).filter(Task.project_id.in_(project_ids), Task.is_deleted == False).order_by(Task.created_at.desc())


def get_assigned_project_ids(db: Session, user_id: int):
    return (
        db.query(Task.project_id)
        .join(TaskAssignment)
        .filter(TaskAssignment.user_id == user_id, TaskAssignment.is_deleted == False, Task.is_deleted == False)
        .distinct()
        .subquery()
    )


def has_assigned_task(db: Session, project_id: int, user_id: int):
    return (
        db.query(Task)
        .join(TaskAssignment)
        .filter(Task.project_id == project_id, TaskAssignment.user_id == user_id, TaskAssignment.is_deleted == False, Task.is_deleted == False)
        .first()
    )


def filter_tasks(query, title: str, project_id: int, employee_id: int, status: str, priority: str):
    if title:
        query = query.filter(Task.title.ilike(f"%{title}%"))
    if project_id is not None:
        query = query.filter(Task.project_id == project_id)
    if employee_id is not None:
        assigned_task_ids = query.session.query(TaskAssignment.task_id).filter(
            TaskAssignment.user_id == employee_id, TaskAssignment.is_deleted == False
        )
        query = query.filter(Task.id.in_(assigned_task_ids))
    if status:
        query = query.filter(Task.status == status)
    if priority:
        query = query.filter(Task.priority == priority)
    return query


def check_task_access(db: Session, task, current_user):
    if current_user.role == "employee" and current_user.id not in task.assignee_ids:
        raise HTTPException(status_code=403, detail="You don't have permission")

    if current_user.role == "manager":
        from app.projects import service as project_service
        project = project_service.find_by_id(db, task.project_id)
        if not project or current_user.id not in project.assignee_ids:
            raise HTTPException(status_code=403, detail="You don't have permission")


def check_manager_task_access(db: Session, task, current_user):
    if current_user.role == "manager":
        from app.projects import service as project_service
        project = project_service.find_by_id(db, task.project_id)
        if not project or current_user.id not in project.assignee_ids:
            raise HTTPException(status_code=403, detail="You don't have permission")


# --- Task CRUD ---

def create_task(db: Session, data: dict, current_user, page: int = 1, limit: int = 10):
    from app.projects import service as project_service
    project = project_service.find_by_id(db, data["project_id"])
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail="Cannot create task for a completed or cancelled project")

    if current_user.role == "manager" and current_user.id not in project.assignee_ids:
        raise HTTPException(status_code=403, detail="You don't have permission")

    if data.get("due_date"):
        if project.start_date and data["due_date"] < project.start_date:
            raise HTTPException(status_code=400, detail="Task due date cannot be before project start date")
        if project.end_date and data["due_date"] > project.end_date:
            raise HTTPException(status_code=400, detail="Task due date cannot be after project end date")

    try:
        task = Task(**data, created_by=current_user.id)
        db.add(task)
        db.commit()
        db.refresh(task)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create task")

    return get_tasks(db, current_user, title="", project_id=None, employee_id=None, status="", priority="", page=page, limit=limit)


def get_tasks(db: Session, current_user, title, project_id, employee_id, status, priority, page, limit):
    if status and status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}")
    if priority and priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"Invalid priority. Must be one of: {', '.join(VALID_PRIORITIES)}")

    if current_user.role == "employee":
        employee_id = None

    conditions = ["t.is_deleted = false"]
    params = {"limit": limit, "offset": (page - 1) * limit}

    if current_user.role == "employee":
        conditions.append(
            "t.id IN (SELECT ta2.task_id FROM task_assignments ta2 WHERE ta2.user_id = :user_id AND ta2.is_deleted = false)"
        )
        params["user_id"] = current_user.id
    elif current_user.role == "manager":
        conditions.append(
            "t.project_id IN (SELECT pu2.project_id FROM project_users pu2 WHERE pu2.user_id = :user_id AND pu2.is_deleted = false)"
        )
        params["user_id"] = current_user.id

    if title:
        conditions.append("t.title ILIKE :title")
        params["title"] = f"%{title}%"
    if project_id is not None:
        conditions.append("t.project_id = :project_id")
        params["project_id"] = project_id
    if employee_id is not None:
        conditions.append(
            "t.id IN (SELECT ta3.task_id FROM task_assignments ta3 WHERE ta3.user_id = :employee_id AND ta3.is_deleted = false)"
        )
        params["employee_id"] = employee_id
    if status:
        conditions.append("t.status = :status")
        params["status"] = status
    if priority:
        conditions.append("t.priority = :priority")
        params["priority"] = priority

    where = " AND ".join(conditions)

    sql = f"""
        WITH filtered_tasks AS (
            SELECT t.id, t.title, t.description, t.status, t.priority,
                   t.due_date, t.project_id, t.created_by, t.created_at
            FROM tasks t
            WHERE {where}
        ),
        total_count AS (
            SELECT COUNT(*) AS total FROM filtered_tasks
        ),
        paginated_tasks AS (
            SELECT * FROM filtered_tasks
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        ),
        task_data AS (
            SELECT
                pt.id, pt.title, pt.description, pt.status, pt.priority,
                pt.due_date, pt.project_id, pt.created_by, pt.created_at,
                u.id AS assignee_id, u.name AS assignee_name, u.role AS assignee_role
            FROM paginated_tasks pt
            LEFT JOIN task_assignments ta ON ta.task_id = pt.id AND ta.is_deleted = false
            LEFT JOIN users u ON u.id = ta.user_id AND u.is_deleted = false
        )
        SELECT
            (SELECT total FROM total_count) AS total,
            COALESCE(json_agg(
                json_build_object(
                    'id', td.id,
                    'title', td.title,
                    'description', td.description,
                    'status', td.status,
                    'priority', td.priority,
                    'due_date', td.due_date,
                    'project_id', td.project_id,
                    'created_by', td.created_by,
                    'created_at', td.created_at,
                    'assigned_to', td.assignees
                )
            ), '[]'::json) AS list
        FROM (
            SELECT
                td.id, td.title, td.description, td.status, td.priority,
                td.due_date, td.project_id, td.created_by, td.created_at,
                COALESCE(
                    json_agg(json_build_object('id', td.assignee_id, 'name', td.assignee_name, 'role', td.assignee_role))
                    FILTER (WHERE td.assignee_id IS NOT NULL),
                    '[]'::json
                ) AS assignees
            FROM task_data td
            GROUP BY td.id, td.title, td.description, td.status, td.priority, td.due_date, td.project_id, td.created_by, td.created_at
            ORDER BY td.created_at DESC
        ) td
    """

    row = db.execute(text(sql), params).mappings().one()
    return {
        "list": row["list"],
        "total": row["total"],
        "page": page,
        "limit": limit,
    }


def get_task(db: Session, task_id: int, current_user):
    task = find_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_task_access(db, task, current_user)
    return task.to_dict()


def update_task(db: Session, task_id: int, data: dict, current_user):
    task = find_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_manager_task_access(db, task, current_user)

    from app.projects import service as project_service
    project = project_service.find_by_id(db, task.project_id)
    if project and project.status in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail="Cannot update task when project is completed or cancelled")

    if data.get("due_date") and project:
        if project.start_date and data["due_date"] < project.start_date:
            raise HTTPException(status_code=400, detail="Task due date cannot be before project start date")
        if project.end_date and data["due_date"] > project.end_date:
            raise HTTPException(status_code=400, detail="Task due date cannot be after project end date")

    data.pop("assigned_to", None)

    old_status = task.status
    new_status = data.get("status", old_status)

    try:
        if new_status != old_status:
            create_history(db, task_id, old_status, new_status, current_user.id)

        for key, value in data.items():
            if key in UPDATABLE_FIELDS:
                setattr(task, key, value)
        db.commit()
        db.refresh(task)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update task")

    return task.to_dict()


def delete_task(db: Session, task_id: int, current_user, page: int = 1, limit: int = 10):
    task = find_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_manager_task_access(db, task, current_user)

    try:
        assignments = db.query(TaskAssignment).filter(TaskAssignment.task_id == task_id, TaskAssignment.is_deleted == False).all()
        for a in assignments:
            a.soft_delete()
        attachments = db.query(Attachment).filter(Attachment.task_id == task_id, Attachment.is_deleted == False).all()
        for att in attachments:
            att.soft_delete()
        task.soft_delete()
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete task")

    return get_tasks(db, current_user, title="", project_id=None, employee_id=None, status="", priority="", page=page, limit=limit)


# --- Task assignment ---

def assign_task(db: Session, task_id: int, user_id: int, current_user):
    task = find_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_manager_task_access(db, task, current_user)

    from app.projects import service as project_service
    project = project_service.find_by_id(db, task.project_id)
    if project and project.status in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail="Cannot assign task when project is completed or cancelled")


    user = user_service.find_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=400, detail="User does not exist")

    if user.role != "employee":
        raise HTTPException(status_code=400, detail="Task can only be assigned to an employee")

    if user_id not in project.assignee_ids:
        raise HTTPException(status_code=400, detail="Employee is not part of this project")

    if user_id in task.assignee_ids:
        raise HTTPException(status_code=400, detail="User is already assigned to this task")

    try:
        existing = (
            db.query(TaskAssignment)
            .filter(TaskAssignment.task_id == task_id, TaskAssignment.user_id == user_id, TaskAssignment.is_deleted == True)
            .first()
        )
        if existing:
            existing.is_deleted = False
            existing.deleted_at = None
            existing.assigned_by = current_user.id
        else:
            db.add(TaskAssignment(task_id=task_id, user_id=user_id, assigned_by=current_user.id))
        db.commit()
        db.refresh(task)
        return task.to_dict()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to assign task")


def unassign_task(db: Session, task_id: int, user_id: int, current_user):
    task = find_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_manager_task_access(db, task, current_user)


    user = user_service.find_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=400, detail="User does not exist")

    assignment = (
        db.query(TaskAssignment)
        .filter(TaskAssignment.task_id == task_id, TaskAssignment.user_id == user_id, TaskAssignment.is_deleted == False)
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    try:
        assignment.soft_delete()
        db.commit()
        db.refresh(task)
        return task.to_dict()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to unassign task")


# --- Task status ---

def update_task_status(db: Session, task_id: int, new_status: str, current_user):
    task = find_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_task_access(db, task, current_user)

    from app.projects import service as project_service
    project = project_service.find_by_id(db, task.project_id)
    if project and project.status in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail="Cannot update task status when project is completed or cancelled")

    old_status = task.status

    try:
        if new_status != old_status:
            create_history(db, task_id, old_status, new_status, current_user.id)

        task.status = new_status
        db.commit()
        db.refresh(task)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update task status")

    return task.to_dict()


# --- Task history ---

def create_history(db: Session, task_id: int, old_status: str, new_status: str, changed_by: int):
    entry = TaskHistory(
        task_id=task_id,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by,
    )
    db.add(entry)
    db.flush()


def get_task_history(db: Session, task_id: int, current_user):
    task = find_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_task_access(db, task, current_user)

    history = (
        db.query(TaskHistory)
        .filter(TaskHistory.task_id == task_id, TaskHistory.is_deleted == False)
        .order_by(TaskHistory.changed_at.desc())
        .all()
    )
    return [h.to_dict() for h in history]


# --- Attachments ---

def upload_attachment(db: Session, task_id: int, file, current_user):
    task = find_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_task_access(db, task, current_user)

    if task.status in ("completed", "blocked"):
        raise HTTPException(status_code=400, detail="Cannot upload attachments to a completed or blocked task")

    from app.projects import service as project_service
    project = project_service.find_by_id(db, task.project_id)
    if project and project.status in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail="Cannot upload attachments to a task under a completed or cancelled project")


    if project and project.end_date and project.end_date < date.today():
        raise HTTPException(status_code=400, detail="Cannot upload attachments to a task under an expired project")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not allowed. Supported: pdf, png, jpg, txt")

    stored_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, stored_filename)
    file_size = 0

    try:
        with open(file_path, "wb") as f:
            while chunk := file.file.read(8192):
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    f.close()
                    os.remove(file_path)
                    raise HTTPException(status_code=400, detail="File size exceeds 10 MB limit")
                f.write(chunk)
    except HTTPException:
        raise
    except OSError:
        raise HTTPException(status_code=500, detail="Failed to save file")

    try:
        attachment = Attachment(
            task_id=task_id,
            original_filename=file.filename,
            stored_filename=stored_filename,
            file_path=file_path,
            file_size=file_size,
            uploaded_by=current_user.id,
        )
        db.add(attachment)
        db.commit()
        db.refresh(attachment)
    except SQLAlchemyError:
        db.rollback()
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail="Failed to save attachment record")

    return _get_attachments(db, task_id)


def get_attachments(db: Session, task_id: int, current_user):
    task = find_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_task_access(db, task, current_user)

    return _get_attachments(db, task_id)


def delete_attachment(db: Session, task_id: int, attachment_id: int, current_user):
    task = find_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_task_access(db, task, current_user)

    attachment = (
        db.query(Attachment)
        .filter(Attachment.id == attachment_id, Attachment.task_id == task_id, Attachment.is_deleted == False)
        .first()
    )
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    if current_user.role == "employee" and attachment.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own attachments")

    try:
        attachment.soft_delete()
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete attachment record")

    return _get_attachments(db, task_id)


def _get_attachments(db: Session, task_id: int):
    attachments = (
        db.query(Attachment)
        .filter(Attachment.task_id == task_id, Attachment.is_deleted == False)
        .order_by(Attachment.uploaded_at.desc())
        .all()
    )
    return [a.to_dict() for a in attachments]
