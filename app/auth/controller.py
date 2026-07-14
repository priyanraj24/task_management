from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.service import find_user_by_email, create_user, hash_password, verify_password, create_access_token


def register_user(db: Session, name: str, email: str, password: str):
    if find_user_by_email(db, email):
        raise HTTPException(status_code=409, detail="Email already exists")

    try:
        user = create_user(db, name, email, hash_password(password))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create user")

    token = create_access_token({"id": user.id, "role": user.role})

    return {
        "access_token": token,
        "user": user.to_dict(),
    }


def login_user(db: Session, email: str, password: str):
    user = find_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"id": user.id, "role": user.role})

    return {
        "access_token": token,
        "user": user.to_dict(),
    }
