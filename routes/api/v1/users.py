from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from authentication.user.dependencies import get_current_user
from authentication.user.request import UserLoginRequest, UserRequest
from authentication.user.response import UserLoginResponse, UserResponse
from authentication.user.utils import create_access_token, get_password_hash, verify_password
from db.session import get_db


router = APIRouter()


def to_user_response(user: dict) -> UserResponse:
    return UserResponse(
        username=user["username"],
        email=user["email"],
        role=user["role"],
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_request: UserRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    email = str(user_request.email).strip().lower()
    user = {
        "email": email,
        "username": user_request.username.strip(),
        "hashed_password": get_password_hash(user_request.password),
        "role": "user",
        "created_at": datetime.now(timezone.utc),
    }

    try:
        await db.users.insert_one(user)
    except DuplicateKeyError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered") from error

    return to_user_response(user)


@router.post("/login", response_model=UserLoginResponse)
async def login_user(
    user_login_request: UserLoginRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    email = str(user_login_request.email).strip().lower()
    user = await db.users.find_one({"email": email})
    if user is None or not verify_password(user_login_request.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    access_token = create_access_token(data={"sub": user["email"]})
    return UserLoginResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: dict = Depends(get_current_user)):
    return to_user_response(current_user)
