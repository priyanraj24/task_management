from sqlalchemy.orm import Session

from app.tasks import service


def create_task(db: Session, data: dict, current_user, page: int = 1, limit: int = 10):
    return service.create_task(db, data, current_user, page, limit)


def get_tasks(db: Session, current_user, title, project_id, employee_id, status, priority, page, limit):
    return service.get_tasks(db, current_user, title, project_id, employee_id, status, priority, page, limit)


def get_task(db: Session, task_id: int, current_user):
    return service.get_task(db, task_id, current_user)


def update_task(db: Session, task_id: int, data: dict, current_user):
    return service.update_task(db, task_id, data, current_user)


def delete_task(db: Session, task_id: int, current_user, page: int = 1, limit: int = 10):
    return service.delete_task(db, task_id, current_user, page, limit)


def assign_task(db: Session, task_id: int, user_id: int, current_user):
    return service.assign_task(db, task_id, user_id, current_user)


def unassign_task(db: Session, task_id: int, user_id: int, current_user):
    return service.unassign_task(db, task_id, user_id, current_user)


def update_task_status(db: Session, task_id: int, new_status: str, current_user):
    return service.update_task_status(db, task_id, new_status, current_user)


def get_task_history(db: Session, task_id: int, current_user):
    return service.get_task_history(db, task_id, current_user)


def upload_attachment(db: Session, task_id: int, file, current_user):
    return service.upload_attachment(db, task_id, file, current_user)


def get_attachments(db: Session, task_id: int, current_user):
    return service.get_attachments(db, task_id, current_user)


def delete_attachment(db: Session, task_id: int, attachment_id: int, current_user):
    return service.delete_attachment(db, task_id, attachment_id, current_user)
