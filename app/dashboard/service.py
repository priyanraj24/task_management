from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


ADMIN_QUERY = """
    WITH project_summary AS (
        SELECT
            COUNT(*) AS total_projects,
            COUNT(*) FILTER (WHERE status = 'active') AS active_projects
        FROM projects
        WHERE is_deleted = false
    ),
    task_summary AS (
        SELECT
            COUNT(*) AS total_tasks,
            COUNT(*) FILTER (WHERE status = 'todo') AS todo_tasks,
            COUNT(*) FILTER (WHERE status = 'in_progress') AS in_progress_tasks,
            COUNT(*) FILTER (WHERE status = 'completed') AS completed_tasks,
            COUNT(*) FILTER (WHERE status = 'blocked') AS blocked_tasks,
            COUNT(*) FILTER (WHERE due_date < CURRENT_DATE AND status NOT IN ('completed', 'blocked')) AS overdue_tasks
        FROM tasks
        WHERE is_deleted = false
    )
    SELECT * FROM project_summary, task_summary
"""

MANAGER_QUERY = """
    WITH manager_projects AS (
        SELECT pu.project_id AS id FROM project_users pu
        JOIN projects p ON p.id = pu.project_id
        WHERE pu.user_id = :user_id AND pu.is_deleted = false AND p.is_deleted = false
    ),
    project_summary AS (
        SELECT
            COUNT(*) AS total_projects,
            COUNT(*) FILTER (WHERE p.status = 'active') AS active_projects
        FROM projects p
        WHERE p.id IN (SELECT id FROM manager_projects) AND p.is_deleted = false
    ),
    task_summary AS (
        SELECT
            COUNT(*) AS total_tasks,
            COUNT(*) FILTER (WHERE t.status = 'todo') AS todo_tasks,
            COUNT(*) FILTER (WHERE t.status = 'in_progress') AS in_progress_tasks,
            COUNT(*) FILTER (WHERE t.status = 'completed') AS completed_tasks,
            COUNT(*) FILTER (WHERE t.status = 'blocked') AS blocked_tasks,
            COUNT(*) FILTER (WHERE t.due_date < CURRENT_DATE AND t.status NOT IN ('completed', 'blocked')) AS overdue_tasks
        FROM tasks t
        WHERE t.project_id IN (SELECT id FROM manager_projects) AND t.is_deleted = false
    )
    SELECT * FROM project_summary, task_summary
"""

EMPLOYEE_QUERY = """
    WITH assigned_tasks AS (
        SELECT t.* FROM tasks t
        JOIN task_assignments ta ON ta.task_id = t.id
        WHERE ta.user_id = :user_id AND ta.is_deleted = false AND t.is_deleted = false
    ),
    project_summary AS (
        SELECT
            COUNT(*) AS total_projects,
            COUNT(*) FILTER (WHERE p.status = 'active') AS active_projects
        FROM projects p
        WHERE p.id IN (SELECT DISTINCT project_id FROM assigned_tasks) AND p.is_deleted = false
    ),
    task_summary AS (
        SELECT
            COUNT(*) AS total_tasks,
            COUNT(*) FILTER (WHERE status = 'todo') AS todo_tasks,
            COUNT(*) FILTER (WHERE status = 'in_progress') AS in_progress_tasks,
            COUNT(*) FILTER (WHERE status = 'completed') AS completed_tasks,
            COUNT(*) FILTER (WHERE status = 'blocked') AS blocked_tasks,
            COUNT(*) FILTER (WHERE due_date < CURRENT_DATE AND status NOT IN ('completed', 'blocked')) AS overdue_tasks
        FROM assigned_tasks
    )
    SELECT * FROM project_summary, task_summary
"""

QUERIES = {
    "admin": ADMIN_QUERY,
    "manager": MANAGER_QUERY,
    "employee": EMPLOYEE_QUERY,
}


def get_summary(db: Session, current_user):
    sql = QUERIES.get(current_user.role)
    if not sql:
        raise HTTPException(status_code=400, detail=f"Unknown role: {current_user.role}")

    params = {"user_id": current_user.id} if current_user.role != "admin" else {}

    try:
        row = db.execute(text(sql), params).mappings().one()
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
