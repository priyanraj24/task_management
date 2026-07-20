from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.projects.schemas import ProjectCreate, ProjectUpdate, ProjectAssign
from app.tasks.schemas import TaskCreate
from app.auth.dependencies import get_current_user, require_roles
from app.projects import controller
from app.tasks import controller as task_controller
from app.response import success_response

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("/", status_code=201)
def create_project(
    project: ProjectCreate,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "manager")),
):
    data = controller.create_project(db, project.model_dump(), current_user, page, limit)
    return success_response(message="Project created successfully", data=data)


@router.get("/")
def get_projects(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    name: str = Query("", max_length=100),
    status: str = Query("", max_length=20),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = controller.get_projects(db, current_user, name, status, page, limit)
    return success_response(message="Projects retrieved successfully", data=data)


@router.get("/{project_id}")
def get_project(
    project_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = controller.get_project(db, project_id, current_user)
    return success_response(message="Project retrieved successfully", data=data)


@router.put("/{project_id}")
def update_project(
    project: ProjectUpdate,
    project_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "manager")),
):
    data = controller.update_project(db, project_id, project.model_dump(exclude_none=True), current_user)
    return success_response(message="Project updated successfully", data=data)


@router.post("/{project_id}/assign")
def assign_project(
    body: ProjectAssign,
    project_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "manager")),
):
    data = controller.assign_project(db, project_id, body.user_id, current_user)
    return success_response(message="Project assigned successfully", data=data)


@router.delete("/{project_id}/unassign")
def unassign_project(
    body: ProjectAssign,
    project_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "manager")),
):
    data = controller.unassign_project(db, project_id, body.user_id, current_user)
    return success_response(message="Project unassigned successfully", data=data)


@router.get("/{project_id}/tasks")
def get_project_tasks(
    project_id: int = Path(ge=1),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = controller.get_project_tasks(db, project_id, current_user, page, limit)
    return success_response(message="Project tasks retrieved successfully", data=data)


@router.post("/{project_id}/tasks", status_code=201)
def create_task(
    task: TaskCreate,
    project_id: int = Path(ge=1),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "manager")),
):
    data = task.model_dump()
    data["project_id"] = project_id
    result = task_controller.create_task(db, data, current_user, page, limit)
    return success_response(message="Task created successfully", data=result)


@router.delete("/{project_id}")
def delete_project(
    project_id: int = Path(ge=1),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "manager")),
):
    data = controller.delete_project(db, project_id, current_user, page, limit)
    return success_response(message="Project deleted successfully", data=data)
