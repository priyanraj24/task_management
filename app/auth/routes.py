from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.users.models import User
from app.auth.schemas import UserRegister, UserLogin
from app.auth.dependencies import get_current_user
from app.auth import controller
from app.response import success_response

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=201)
def register(user: UserRegister, db: Session = Depends(get_db)):
    data = controller.register_user(db, user.name, user.email, user.password)
    return success_response(message="User registered successfully", data=data)


@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    data = controller.login_user(db, user.email, user.password)
    return success_response(message="Login successful", data=data)


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return success_response(message="User profile retrieved successfully", data=current_user.to_dict())
