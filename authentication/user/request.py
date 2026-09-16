from pydantic import BaseModel
from typing import Optional

class UserRequest(BaseModel):
    username: str
    email: str
    password: str
    role : Optional[str] = "user"

class AdminUserRequest(UserRequest):
    role: str = "superuser"

class UserUpdateRequest(BaseModel):
    username: str | None = None
    email: str | None = None
    password: str | None = None

class UserLoginRequest(BaseModel):
    email: str
    password: str


