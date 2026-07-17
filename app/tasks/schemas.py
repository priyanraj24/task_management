from pydantic import BaseModel, field_validator
from datetime import date
from typing import Optional


VALID_STATUSES = ("todo", "in_progress", "completed", "blocked")
VALID_PRIORITIES = ("low", "medium", "high", "critical")


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str
    due_date: date

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Title must be at least 3 characters")
        if len(v) > 100:
            raise ValueError("Title must not exceed 100 characters")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v):
        if v is not None and len(v) > 255:
            raise ValueError("Description must not exceed 255 characters")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v):
        v = v.lower().strip()
        if v not in VALID_PRIORITIES:
            raise ValueError(f"Invalid priority. Must be one of: {', '.join(VALID_PRIORITIES)}")
        return v

    @field_validator("due_date")
    @classmethod
    def due_date_not_past(cls, v):
        if v < date.today():
            raise ValueError("Due date cannot be in the past")
        return v


class TaskAssign(BaseModel):
    user_id: int

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v):
        if v < 1:
            raise ValueError("User ID must be at least 1")
        return v


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[date] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        if v is None:
            return v
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Title must be at least 3 characters")
        if len(v) > 100:
            raise ValueError("Title must not exceed 100 characters")
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
        if v is None:
            return v
        v = v.lower().strip()
        if v not in VALID_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v):
        if v is None:
            return v
        v = v.lower().strip()
        if v not in VALID_PRIORITIES:
            raise ValueError(f"Invalid priority. Must be one of: {', '.join(VALID_PRIORITIES)}")
        return v



class TaskStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        v = v.lower().strip()
        if v not in VALID_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}")
        return v
