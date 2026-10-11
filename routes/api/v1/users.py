from datetime import UTC, datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from authentication.user.dependencies import get_current_superuser, get_current_user
from authentication.user.request import UserLoginRequest, UserRequest, UserUpdateRequest
from authentication.user.response import UserLoginResponse, UserResponse
from authentication.user.utils import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from db.session import get_db

router = APIRouter()


def to_user_response(user: dict) -> UserResponse:
    return UserResponse(
        username=user["username"],
        email=user["email"],
        role=user["role"],
    )


async def get_user_or_404(db: AsyncIOMotorDatabase, user_id: str) -> dict:
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


async def apply_user_update(
    db: AsyncIOMotorDatabase,
    current_user: dict,
    user_update: UserUpdateRequest,
) -> dict:
    update_data: dict[str, str] = {}

    if user_update.username is not None:
        update_data["username"] = user_update.username.strip()
    if user_update.email is not None:
        email = str(user_update.email).strip().lower()
        existing_user = await db.users.find_one(
            {"email": email, "_id": {"$ne": current_user["_id"]}}
        )
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        update_data["email"] = email
    if user_update.password is not None:
        update_data["hashed_password"] = get_password_hash(user_update.password)

    if not update_data:
        return current_user

    await db.users.update_one({"_id": current_user["_id"]}, {"$set": update_data})
    return {**current_user, **update_data}


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
)
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
        "created_at": datetime.now(UTC),
    }

    try:
        await db.users.insert_one(user)
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        ) from error

    return to_user_response(user)


@router.post("/login", response_model=UserLoginResponse, tags=["Authentication"])
async def login_user(
    user_login_request: UserLoginRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    email = str(user_login_request.email).strip().lower()
    user = await db.users.find_one({"email": email})
    if user is None or not verify_password(
        user_login_request.password, user["hashed_password"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(data={"sub": user["email"]})
    return UserLoginResponse(access_token=access_token)


@router.post(
    "/token",
    response_model=UserLoginResponse,
    include_in_schema=False,
    tags=["Authentication"],
)
async def token_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    email = form_data.username.strip().lower()
    user = await db.users.find_one({"email": email})
    if user is None or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(data={"sub": user["email"]})
    return UserLoginResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse, tags=["My Profile"])
async def get_profile(current_user: dict = Depends(get_current_user)):
    return to_user_response(current_user)


@router.patch("/me", response_model=UserResponse, tags=["My Profile"])
async def update_profile(
    user_update: UserUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    updated_user = await apply_user_update(db, current_user, user_update)
    return to_user_response(updated_user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, tags=["My Profile"])
async def delete_profile(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    await db.users.delete_one({"_id": current_user["_id"]})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/admin/users", response_model=list[UserResponse], tags=["Admin Users"])
async def list_users(
    current_user: dict = Depends(get_current_superuser),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    users = await db.users.find({}).sort("username", 1).to_list(length=None)
    return [to_user_response(user) for user in users]


@router.get(
    "/admin/users/{user_id}",
    response_model=UserResponse,
    tags=["Admin Users"],
)
async def get_user_by_id(
    user_id: str,
    current_user: dict = Depends(get_current_superuser),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user = await get_user_or_404(db, user_id)
    return to_user_response(user)


@router.patch(
    "/admin/users/{user_id}",
    response_model=UserResponse,
    tags=["Admin Users"],
)
async def update_user_by_id(
    user_id: str,
    user_update: UserUpdateRequest,
    current_user: dict = Depends(get_current_superuser),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user = await get_user_or_404(db, user_id)
    updated_user = await apply_user_update(db, user, user_update)
    return to_user_response(updated_user)


@router.delete(
    "/admin/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Admin Users"],
)
async def delete_user_by_id(
    user_id: str,
    current_user: dict = Depends(get_current_superuser),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user = await get_user_or_404(db, user_id)
    await db.users.delete_one({"_id": user["_id"]})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/admin/users/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Admin Users"],
)
async def create_admin_user(
    user_request: UserRequest,
    current_user: dict = Depends(get_current_superuser),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    email = str(user_request.email).strip().lower()
    user = {
        "email": email,
        "username": user_request.username.strip(),
        "hashed_password": get_password_hash(user_request.password),
        "role": "superuser",
        "created_at": datetime.now(UTC),
    }

    try:
        await db.users.insert_one(user)
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        ) from error

    return to_user_response(user)
