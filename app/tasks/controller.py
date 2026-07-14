import os
import uuid

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.tasks import service
from app.tasks.schemas import VALID_STATUSES, VALID_PRIORITIES
from app.projects import service as project_service
from app.users import service as user_service


UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt"}


def _get_scoped_query(db: Session, current_user):
    if current_user.role == "employee":
        return service.get_by_assignee(db, current_user.id)
    elif current_user.role == "manager":
        from app.projects.models import Project
        from sqlalchemy import or_
        manager_project_ids = (
            db.query(Project.id)
            .filter(
                or_(Project.assigned_to == current_user.id, Project.created_by == current_user.id),
                Project.is_deleted == False,
            )
            .subquery()
        )
        return service.get_by_project_ids(db, manager_project_ids)
    return service.get_all(db)


def check_task_access(db: Session, task, current_user):
    if current_user.role == "employee" and task.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="You don't have permission")

    if current_user.role == "manager":
        project = project_service.find_by_id(db, task.project_id)
        if not project or (project.assigned_to != current_user.id and project.created_by != current_user.id):
            raise HTTPException(status_code=403, detail="You don't have permission")


def create_task(db: Session, data: dict, current_user):
    project = project_service.find_by_id(db, data["project_id"])
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role == "manager" and project.assigned_to != current_user.id and project.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="You don't have permission")

    if data.get("assigned_to") is not None:
        assigned_user = user_service.find_by_id(db, data["assigned_to"])
        if not assigned_user:
            raise HTTPException(status_code=400, detail="Assigned user does not exist")
        if assigned_user.role != "employee":
            raise HTTPException(status_code=400, detail="Task can only be assigned to an employee")

    try:
        service.create_task(db, **data, created_by=current_user.id)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create task")

    return [t.to_dict() for t in _get_scoped_query(db, current_user).all()]


def get_tasks(db: Session, current_user, status, priority, project_id, page, limit):
    query = _get_scoped_query(db, current_user)
    if status and status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}")
    if priority and priority not in VALID_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"Invalid priority. Must be one of: {', '.join(VALID_PRIORITIES)}")

    from app.database import paginate
    query = service.filter_tasks(query, status, priority, project_id)
    tasks, total = paginate(query, page, limit)
    return {
        "list": [t.to_dict() for t in tasks],
        "total": total,
        "page": page,
        "limit": limit,
    }


def get_task(db: Session, task_id: int, current_user):
    task = service.find_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_task_access(db, task, current_user)
    return task.to_dict()


def update_task(db: Session, task_id: int, data: dict, current_user):
    task = service.find_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if current_user.role == "manager":
        project = project_service.find_by_id(db, task.project_id)
        if not project or (project.assigned_to != current_user.id and project.created_by != current_user.id):
            raise HTTPException(status_code=403, detail="You don't have permission")

    if data.get("assigned_to") is not None:
        assigned_user = user_service.find_by_id(db, data["assigned_to"])
        if not assigned_user:
            raise HTTPException(status_code=400, detail="Assigned user does not exist")
        if assigned_user.role != "employee":
            raise HTTPException(status_code=400, detail="Task can only be assigned to an employee")

    old_status = task.status

    try:
        if data["status"] != old_status:
            service.create_history(db, task_id, old_status, data["status"], current_user.id)

        service.update_task(db, task, data)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update task")

    return task.to_dict()


def delete_task(db: Session, task_id: int, current_user):
    task = service.find_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        service.soft_delete_task(db, task)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete task")

    return [t.to_dict() for t in _get_scoped_query(db, current_user).all()]


def update_task_status(db: Session, task_id: int, new_status: str, current_user):
    task = service.find_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_task_access(db, task, current_user)

    old_status = task.status

    try:
        if new_status != old_status:
            service.create_history(db, task_id, old_status, new_status, current_user.id)

        service.update_task(db, task, {"status": new_status})
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update task status")

    return task.to_dict()


def get_task_history(db: Session, task_id: int, current_user):
    task = service.find_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_task_access(db, task, current_user)

    history = service.get_history(db, task_id)
    return [h.to_dict() for h in history]


def upload_attachment(db: Session, task_id: int, file, current_user):
    task = service.find_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_task_access(db, task, current_user)

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
        service.create_attachment(
            db,
            task_id=task_id,
            original_filename=file.filename,
            stored_filename=stored_filename,
            file_path=file_path,
            file_size=file_size,
            uploaded_by=current_user.id,
        )
    except SQLAlchemyError:
        db.rollback()
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail="Failed to save attachment record")

    return [a.to_dict() for a in service.get_attachments(db, task_id)]


def get_attachments(db: Session, task_id: int, current_user):
    task = service.find_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_task_access(db, task, current_user)

    return [a.to_dict() for a in service.get_attachments(db, task_id)]


def delete_attachment(db: Session, task_id: int, attachment_id: int, current_user):
    task = service.find_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    check_task_access(db, task, current_user)

    attachment = service.find_attachment(db, attachment_id, task_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    if current_user.role == "employee" and attachment.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own attachments")

    try:
        service.soft_delete_attachment(db, attachment)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete attachment record")

    return [a.to_dict() for a in service.get_attachments(db, task_id)]
