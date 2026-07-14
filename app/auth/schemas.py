import re

from pydantic import BaseModel, EmailStr, field_validator

NAME_REGEX = re.compile(r"^[a-zA-Z\s]+$")


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Name must be at least 3 characters")
        if len(v) > 255:
            raise ValueError("Name must not exceed 255 characters")
        if not NAME_REGEX.match(v):
            raise ValueError("Name can only contain letters and spaces")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 20:
            raise ValueError("Password must not exceed 20 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:',.<>?/`~" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str
