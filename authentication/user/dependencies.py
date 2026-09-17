from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorDatabase

from authentication.user.utils import decode_access_token
from db.session import get_db


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/users/token",
    description="Enter your account email address in the Username field.",
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        email = payload.get("sub")
        if not isinstance(email, str):
            raise credentials_error
    except Exception as error:
        if isinstance(error, HTTPException):
            raise
        raise credentials_error from error

    user = await db.users.find_one({"email": email})
    if user is None:
        raise credentials_error
    return user


def require_role(role: str):
    async def role_dependency(
        current_user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        if current_user.get("role") != role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return role_dependency


async def get_current_superuser(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    role = current_user.get("role")
    if role != "superuser":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Superuser privileges required; current role is {role!r}",
        )
    return current_user