from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.dashboard import service


def get_summary(db: Session, current_user):
    try:
        row = service.get_summary(db, current_user.role, current_user.id)
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard summary")

    return {
        "total_projects": row["total_projects"],
        "active_projects": row["active_projects"],
        "total_tasks": row["total_tasks"],
        "todo_tasks": row["todo_tasks"],
        "in_progress_tasks": row["in_progress_tasks"],
        "completed_tasks": row["completed_tasks"],
        "blocked_tasks": row["blocked_tasks"],
        "overdue_tasks": row["overdue_tasks"],
    }
