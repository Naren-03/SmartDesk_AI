from pydantic import BaseModel


class UserLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminUserLoginResponse(UserLoginResponse):
    role: str = "superuser"


class UserResponse(BaseModel):
    username: str
    email: str
    role: str
