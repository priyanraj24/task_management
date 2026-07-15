from sqlalchemy.orm import Session

from app.users import service


def get_users(db: Session, page: int, limit: int, current_user_id: int, name: str = "", email: str = "", role: str = ""):
    return service.get_users(db, page, limit, current_user_id, name, email, role)


def get_user(db: Session, user_id: int):
    return service.get_user(db, user_id)


def update_user(db: Session, user_id: int, data: dict, current_user_id: int, page: int = 1, limit: int = 10):
    return service.update_user(db, user_id, data, current_user_id, page, limit)


def delete_user(db: Session, user_id: int, current_user_id: int, page: int = 1, limit: int = 10):
    return service.delete_user(db, user_id, current_user_id, page, limit)
