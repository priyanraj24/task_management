from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.projects.models import Project


def find_by_id(db: Session, project_id: int):
    return db.query(Project).filter(Project.id == project_id, Project.is_deleted == False).first()


def find_by_name(db: Session, name: str):
    return db.query(Project).filter(Project.name == name, Project.is_deleted == False).first()


def create(db: Session, **kwargs):
    project = Project(**kwargs)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


UPDATABLE_FIELDS = {"name", "description", "status", "start_date", "end_date", "assigned_to"}


def update(db: Session, project: Project, data: dict):
    for key, value in data.items():
        if key in UPDATABLE_FIELDS:
            setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


def soft_delete(db: Session, project: Project):
    project.soft_delete()
    db.commit()


def get_all(db: Session):
    return db.query(Project).filter(Project.is_deleted == False).order_by(Project.created_at.desc())


def get_by_manager(db: Session, user_id: int):
    return db.query(Project).filter(
        or_(Project.assigned_to == user_id, Project.created_by == user_id),
        Project.is_deleted == False,
    ).order_by(Project.created_at.desc())


def get_by_ids(db: Session, project_ids):
    return db.query(Project).filter(Project.id.in_(project_ids), Project.is_deleted == False).order_by(Project.created_at.desc())


def filter_projects(query, search: str, status: str):
    if search:
        query = query.filter(Project.name.ilike(f"%{search}%"))
    if status:
        query = query.filter(Project.status == status)
    return query
