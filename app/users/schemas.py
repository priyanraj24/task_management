import re

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional

NAME_REGEX = re.compile(r"^[a-zA-Z\s]+$")
VALID_ROLES = ("admin", "manager", "employee")


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if v is None:
            return v
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Name must be at least 3 characters")
        if len(v) > 100:
            raise ValueError("Name must not exceed 100 characters")
        if not NAME_REGEX.match(v):
            raise ValueError("Name can only contain letters and spaces")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v is None:
            return v
        v = v.lower().strip()
        if v not in VALID_ROLES:
            raise ValueError(f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")
        return v
