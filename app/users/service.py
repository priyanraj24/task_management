from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.projects.models import Project, ProjectUser
from app.tasks.models import Task, TaskAssignment, TaskHistory, Attachment
from app.users.models import User


UPDATABLE_FIELDS = {"name", "email", "role"}


def find_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id, User.is_deleted == False).first()


def find_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email, User.is_deleted == False).first()


def get_users(db: Session, page: int, limit: int, current_user_id: int, name: str = "", email: str = "", role: str = ""):
    if role and role not in ("admin", "manager", "employee"):
        raise HTTPException(status_code=400, detail="Invalid role. Must be one of: admin, manager, employee")

    conditions = ["u.is_deleted = false", "u.id != :current_user_id"]
    params = {"current_user_id": current_user_id, "limit": limit, "offset": (page - 1) * limit}

    if name:
        conditions.append("u.name ILIKE :name")
        params["name"] = f"%{name}%"
    if email:
        conditions.append("u.email ILIKE :email")
        params["email"] = f"%{email}%"
    if role:
        conditions.append("u.role = :role")
        params["role"] = role

    where = " AND ".join(conditions)

    sql = f"""
        WITH filtered_users AS (
            SELECT u.id, u.name, u.email, u.role, u.created_at
            FROM users u
            WHERE {where}
        ),
        total_count AS (
            SELECT COUNT(*) AS total FROM filtered_users
        ),
        paginated_users AS (
            SELECT * FROM filtered_users
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        )
        SELECT
            (SELECT total FROM total_count) AS total,
            COALESCE(json_agg(
                json_build_object(
                    'id', pu.id,
                    'name', pu.name,
                    'email', pu.email,
                    'role', pu.role,
                    'created_at', pu.created_at
                )
            ), '[]'::json) AS list
        FROM paginated_users pu
    """

    row = db.execute(text(sql), params).mappings().one()
    return {
        "list": row["list"],
        "total": row["total"],
        "page": page,
        "limit": limit,
    }


def get_user(db: Session, user_id: int):
    user = find_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_dict()


def update_user(db: Session, user_id: int, data: dict, current_user_id: int, page: int = 1, limit: int = 10):
    user = find_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == "admin" and user.id != current_user_id:
        raise HTTPException(status_code=403, detail="Cannot edit another admin")

    if user.id == current_user_id and data.get("role") and data["role"] != user.role:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    update_data = {k: v for k, v in data.items() if v is not None}

    if "email" in update_data and update_data["email"] != user.email:
        if find_by_email(db, update_data["email"]):
            raise HTTPException(status_code=409, detail="Email already exists")

    try:
        for key, value in update_data.items():
            if key in UPDATABLE_FIELDS:
                setattr(user, key, value)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update user")

    return get_users(db, page, limit, current_user_id)


def delete_user(db: Session, user_id: int, current_user_id: int, page: int = 1, limit: int = 10):
    if user_id == current_user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    user = find_by_id(db, user_id)
    if not user:
        return get_users(db, page, limit, current_user_id)

    if user.role == "admin":
        raise HTTPException(status_code=403, detail="Cannot delete another admin")

    try:
        db.query(Project).filter(Project.created_by == user_id).update({"created_by": None})
        db.query(Task).filter(Task.created_by == user_id).update({"created_by": None})
        db.query(ProjectUser).filter(ProjectUser.assigned_by == user_id).update({"assigned_by": None})
        db.query(TaskAssignment).filter(TaskAssignment.assigned_by == user_id).update({"assigned_by": None})
        db.query(TaskHistory).filter(TaskHistory.changed_by == user_id).update({"changed_by": None})
        db.query(Attachment).filter(Attachment.uploaded_by == user_id).update({"uploaded_by": None})
        project_assignments = db.query(ProjectUser).filter(ProjectUser.user_id == user_id, ProjectUser.is_deleted == False).all()
        for pa in project_assignments:
            pa.soft_delete()
        task_assignments = db.query(TaskAssignment).filter(TaskAssignment.user_id == user_id, TaskAssignment.is_deleted == False).all()
        for ta in task_assignments:
            ta.soft_delete()
        user.soft_delete()
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete user")

    return get_users(db, page, limit, current_user_id)
