from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.dashboard import controller
from app.response import success_response

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def get_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    data = controller.get_summary(db, current_user)
    return success_response(message="Dashboard summary retrieved successfully", data=data)
