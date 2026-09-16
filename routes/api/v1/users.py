from authentication.user.models import User
from authentication.user.request import UserRequest, AdminUserRequest, UserUpdateRequest, UserLoginRequest
from authentication.user.response import UserLoginResponse, UserResponse
from authentication.user.utils import create_access_token, get_password_hash, verify_password
from fastapi import APIRouter, HTTPException, Depends
from db.session import db
import datetime


router = APIRouter()

def get_db():
    return db


@router.post("/register", response_model=UserResponse)
async def register_user(user_request: UserRequest, db=Depends(get_db)):
    existing_user = await db.users.find_one({"email": user_request.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user_request.password)

    if user_request.role == "superuser":
        await db.users.insert_one({
            "email": user_request.email,
            "name": user_request.username,
            "hashed_password": hashed_password,
            "role": "superuser",
            "created_at": datetime.datetime.now() 

         })
        return UserResponse(email=user_request.email, username=user_request.username, role="superuser")
    else:
        await db.users.insert_one({
            "email": user_request.email,
            "name": user_request.username,
            "hashed_password": hashed_password,
            "role": "user",
            "created_at": datetime.datetime.now()
            })
        
        return UserResponse(email=user_request.email, username=user_request.username, role="user")





@router.post("/login", response_model=UserLoginResponse)
async def login_user(user_login_request: UserLoginRequest, db=Depends(get_db)):
    user = await db.users.find_one({"email": user_login_request.email})
    if not user or not verify_password(user_login_request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    access_token = create_access_token(data={"sub": user["email"]})
    return UserLoginResponse(access_token=access_token)







