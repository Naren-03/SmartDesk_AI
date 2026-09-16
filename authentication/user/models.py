from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    SUPERUSER = "superuser"
    USER = "user"


class User(BaseModel):
    
    username: str = Field(..., description="The user's username")
    email: EmailStr = Field(..., description="The user's email address")
    password: str = Field(..., description="The user's password")
    role: UserRole = Field(description="The user's role in the system",default=UserRole.USER.value)
    created_at: datetime = Field(..., description="The timestamp when the user was created")