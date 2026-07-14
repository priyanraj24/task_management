from sqlalchemy.orm import Session
from sqlalchemy import text


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
        SELECT id FROM projects WHERE (assigned_to = :user_id OR created_by = :user_id) AND is_deleted = false
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
        SELECT * FROM tasks WHERE assigned_to = :user_id AND is_deleted = false
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


def get_summary(db: Session, role: str, user_id: int):
    sql = QUERIES.get(role)
    if not sql:
        raise ValueError(f"Unknown role: {role}")
    params = {"user_id": user_id} if role != "admin" else {}
    return db.execute(text(sql), params).mappings().one()
