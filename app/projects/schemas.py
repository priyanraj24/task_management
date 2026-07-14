from pydantic import BaseModel, field_validator
from datetime import date
from typing import Optional


VALID_PROJECT_STATUSES = ("planned", "active", "completed", "cancelled")


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: date
    end_date: date

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Project name must be at least 3 characters")
        if len(v) > 255:
            raise ValueError("Project name must not exceed 255 characters")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v):
        if v is not None and len(v) > 255:
            raise ValueError("Description must not exceed 255 characters")
        return v


class ProjectAssign(BaseModel):
    user_id: int

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v):
        if v < 1:
            raise ValueError("User ID must be at least 1")
        return v


class ProjectUpdate(BaseModel):
    name: str
    description: Optional[str] = None
    status: str
    start_date: date
    end_date: date

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Project name must be at least 3 characters")
        if len(v) > 255:
            raise ValueError("Project name must not exceed 255 characters")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v):
        if v is not None and len(v) > 255:
            raise ValueError("Description must not exceed 255 characters")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        v = v.lower().strip()
        if v not in VALID_PROJECT_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(VALID_PROJECT_STATUSES)}")
        return v
