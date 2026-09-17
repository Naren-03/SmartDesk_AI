from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr


class UserRole(str, Enum):
    USER = "user"
    SUPERUSER = "superuser"


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str
    email: EmailStr
    hashed_password: str
    role: UserRole = UserRole.USER
    created_at: datetime
