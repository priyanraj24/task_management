from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.users.schemas import UserUpdate
from app.auth.dependencies import require_roles
from app.users import controller
from app.response import success_response

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/")
def get_users(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    data = controller.get_users(db, page, limit, current_user.id)
    return success_response(message="Users retrieved successfully", data=data)


@router.get("/{user_id}")
def get_user(
    user_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    data = controller.get_user(db, user_id)
    return success_response(message="User retrieved successfully", data=data)


@router.put("/{user_id}")
def update_user(
    user: UserUpdate,
    user_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    data = controller.update_user(db, user_id, user.model_dump(exclude_none=True), current_user.id)
    return success_response(message="User updated successfully", data=data)


@router.delete("/{user_id}")
def delete_user(
    user_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    controller.delete_user(db, user_id, current_user.id)
    return success_response(message="User deleted successfully")
