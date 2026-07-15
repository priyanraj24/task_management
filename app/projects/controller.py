from sqlalchemy.orm import Session

from app.projects import service


def create_project(db: Session, data: dict, current_user, page: int = 1, limit: int = 10):
    return service.create_project(db, data, current_user, page, limit)


def get_projects(db: Session, current_user, name: str, status: str, page: int, limit: int):
    return service.get_projects(db, current_user, name, status, page, limit)


def get_project(db: Session, project_id: int, current_user):
    return service.get_project(db, project_id, current_user)


def update_project(db: Session, project_id: int, data: dict, current_user):
    return service.update_project(db, project_id, data, current_user)


def delete_project(db: Session, project_id: int, current_user, page: int = 1, limit: int = 10):
    return service.delete_project(db, project_id, current_user, page, limit)


def get_project_tasks(db: Session, project_id: int, current_user, page: int = 1, limit: int = 10):
    return service.get_project_tasks(db, project_id, current_user, page, limit)


def assign_project(db: Session, project_id: int, user_id: int, current_user):
    return service.assign_project(db, project_id, user_id, current_user)


def unassign_project(db: Session, project_id: int, user_id: int, current_user):
    return service.unassign_project(db, project_id, user_id, current_user)
