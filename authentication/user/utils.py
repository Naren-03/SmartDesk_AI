from datetime import datetime, timedelta,timezone
import jwt
from pwdlib import PasswordHash
from typing import Any



SECRET_KEY = "60cd960b3d4dab8f3ec8842d133c58227d923768fe98b19c76fe99c401a998ac"
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30

password_hasher = PasswordHash.recommended()


def get_password_hash(password: str) -> str:
    return password_hasher.hash(password)


def create_access_token(
    data: dict[str, Any],
    secret_key: str = SECRET_KEY,
    algorithm: str = ALGORITHM,
    expires_delta: int = TOKEN_EXPIRE_MINUTES,
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hasher.verify(plain_password, hashed_password)

