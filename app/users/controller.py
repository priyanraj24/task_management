from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.users import service


def get_users(db: Session, page: int, limit: int, current_user_id: int):
    users, total = service.get_all(db, page, limit, exclude_user_id=current_user_id)
    return {
        "list": [u.to_dict() for u in users],
        "total": total,
        "page": page,
        "limit": limit,
    }


def get_user(db: Session, user_id: int):
    user = service.find_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_dict()


def update_user(db: Session, user_id: int, data: dict):
    user = service.find_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data["email"] != user.email:
        if service.find_by_email(db, data["email"]):
            raise HTTPException(status_code=409, detail="Email already exists")

    try:
        return service.update(db, user, data).to_dict()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update user")


def delete_user(db: Session, user_id: int, current_user_id: int):
    if user_id == current_user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    user = service.find_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        service.soft_delete(db, user)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete user")
