from sqlalchemy.orm import Session

from app.tasks.models import Task, TaskHistory, Attachment


def find_task_by_id(db: Session, task_id: int):
    return db.query(Task).filter(Task.id == task_id, Task.is_deleted == False).first()


def create_task(db: Session, **kwargs):
    task = Task(**kwargs)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


UPDATABLE_FIELDS = {"title", "description", "status", "priority", "due_date", "assigned_to"}


def update_task(db: Session, task: Task, data: dict):
    for key, value in data.items():
        if key in UPDATABLE_FIELDS:
            setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


def soft_delete_task(db: Session, task: Task):
    task.soft_delete()
    db.commit()


def create_history(db: Session, task_id: int, old_status: str, new_status: str, changed_by: int):
    entry = TaskHistory(
        task_id=task_id,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by,
    )
    db.add(entry)
    db.flush()


def get_history(db: Session, task_id: int):
    return (
        db.query(TaskHistory)
        .filter(TaskHistory.task_id == task_id)
        .order_by(TaskHistory.changed_at.desc())
        .all()
    )


def get_all(db: Session):
    return db.query(Task).filter(Task.is_deleted == False).order_by(Task.created_at.desc())


def get_by_assignee(db: Session, user_id: int):
    return db.query(Task).filter(Task.assigned_to == user_id, Task.is_deleted == False).order_by(Task.created_at.desc())


def get_by_project_id(db: Session, project_id: int):
    return db.query(Task).filter(Task.project_id == project_id, Task.is_deleted == False).order_by(Task.created_at.desc()).all()


def get_by_project_ids(db: Session, project_ids):
    return db.query(Task).filter(Task.project_id.in_(project_ids), Task.is_deleted == False).order_by(Task.created_at.desc())


def get_assigned_project_ids(db: Session, user_id: int):
    return (
        db.query(Task.project_id)
        .filter(Task.assigned_to == user_id, Task.is_deleted == False)
        .distinct()
        .subquery()
    )


def has_assigned_task(db: Session, project_id: int, user_id: int):
    return (
        db.query(Task)
        .filter(Task.project_id == project_id, Task.assigned_to == user_id, Task.is_deleted == False)
        .first()
    )


def filter_tasks(query, status: str, priority: str, project_id: int):
    if status:
        query = query.filter(Task.status == status)
    if priority:
        query = query.filter(Task.priority == priority)
    if project_id is not None:
        query = query.filter(Task.project_id == project_id)
    return query




def create_attachment(db: Session, **kwargs):
    attachment = Attachment(**kwargs)
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


def find_attachment(db: Session, attachment_id: int, task_id: int):
    return (
        db.query(Attachment)
        .filter(Attachment.id == attachment_id, Attachment.task_id == task_id, Attachment.is_deleted == False)
        .first()
    )


def soft_delete_attachment(db: Session, attachment: Attachment):
    attachment.soft_delete()
    db.commit()


def get_attachments(db: Session, task_id: int):
    return (
        db.query(Attachment)
        .filter(Attachment.task_id == task_id, Attachment.is_deleted == False)
        .order_by(Attachment.uploaded_at.desc())
        .all()
    )
