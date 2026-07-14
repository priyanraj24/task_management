from sqlalchemy.orm import Session

from app.users.models import User


def find_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id, User.is_deleted == False).first()


def find_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email, User.is_deleted == False).first()


def get_all(db: Session, page: int, limit: int, exclude_user_id: int = None):
    query = db.query(User).filter(User.is_deleted == False).order_by(User.created_at.desc())
    if exclude_user_id:
        query = query.filter(User.id != exclude_user_id)
    from app.database import paginate
    return paginate(query, page, limit)


UPDATABLE_FIELDS = {"name", "email", "role"}


def update(db: Session, user: User, data: dict):
    for key, value in data.items():
        if key in UPDATABLE_FIELDS:
            setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def soft_delete(db: Session, user: User):
    user.soft_delete()
    db.commit()
