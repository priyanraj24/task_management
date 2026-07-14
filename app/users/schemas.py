from pydantic import BaseModel, EmailStr, field_validator


VALID_ROLES = ("admin", "manager", "employee")


class UserUpdate(BaseModel):
    name: str
    email: EmailStr
    role: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Name must be at least 3 characters")
        if len(v) > 255:
            raise ValueError("Name must not exceed 255 characters")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        v = v.lower().strip()
        if v not in VALID_ROLES:
            raise ValueError(f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")
        return v
