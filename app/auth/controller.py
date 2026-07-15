from sqlalchemy.orm import Session

from app.auth import service


def register_user(db: Session, name: str, email: str, password: str):
    return service.register(db, name, email, password)


def login_user(db: Session, email: str, password: str):
    return service.login(db, email, password)
