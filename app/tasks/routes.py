from fastapi import APIRouter, Depends, UploadFile, File, Path, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.tasks.schemas import TaskUpdate, TaskStatusUpdate
from app.auth.dependencies import get_current_user, require_roles
from app.tasks import controller
from app.response import success_response

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/")
def get_tasks(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: str = Query("", max_length=20),
    priority: str = Query("", max_length=20),
    project_id: int = Query(None, ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = controller.get_tasks(db, current_user, status, priority, project_id, page, limit)
    return success_response(message="Tasks retrieved successfully", data=data)


@router.get("/{task_id}")
def get_task(
    task_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = controller.get_task(db, task_id, current_user)
    return success_response(message="Task retrieved successfully", data=data)


@router.put("/{task_id}")
def update_task(
    task: TaskUpdate,
    task_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "manager")),
):
    data = controller.update_task(db, task_id, task.model_dump(exclude_none=True), current_user)
    return success_response(message="Task updated successfully", data=data)


@router.delete("/{task_id}")
def delete_task(
    task_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    tasks = controller.delete_task(db, task_id, current_user)
    return success_response(message="Task deleted successfully", data={"list": tasks})


@router.get("/{task_id}/history")
def get_task_history(
    task_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = controller.get_task_history(db, task_id, current_user)
    return success_response(message="Task history retrieved successfully", data={"list": data})


@router.post("/{task_id}/attachments", status_code=201)
def upload_attachment(
    file: UploadFile = File(...),
    task_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    attachments = controller.upload_attachment(db, task_id, file, current_user)
    return success_response(message="File uploaded successfully", data={"list": attachments})


@router.get("/{task_id}/attachments")
def get_attachments(
    task_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = controller.get_attachments(db, task_id, current_user)
    return success_response(message="Attachments retrieved successfully", data={"list": data})


@router.delete("/{task_id}/attachments/{attachment_id}")
def delete_attachment(
    task_id: int = Path(ge=1),
    attachment_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    attachments = controller.delete_attachment(db, task_id, attachment_id, current_user)
    return success_response(message="Attachment deleted successfully", data={"list": attachments})


@router.patch("/{task_id}/status")
def update_task_status(
    body: TaskStatusUpdate,
    task_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = controller.update_task_status(db, task_id, body.status, current_user)
    return success_response(message="Task status updated successfully", data=data)
