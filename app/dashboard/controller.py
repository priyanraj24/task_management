from sqlalchemy.orm import Session

from app.dashboard import service


def get_summary(db: Session, current_user):
    return service.get_summary(db, current_user)
