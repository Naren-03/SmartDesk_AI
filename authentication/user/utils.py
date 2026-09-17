from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash

from core.config import settings


password_hasher = PasswordHash.recommended()


def get_password_hash(password: str) -> str:
    return password_hasher.hash(password)


def create_access_token(data: dict[str, Any]) -> str:
    now = datetime.now(timezone.utc)
    to_encode = data.copy()
    to_encode.update(
        {
            "exp": now + timedelta(minutes=settings.token_expire_minutes),
            "iat": now,
        }
    )
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm],
    )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hasher.verify(plain_password, hashed_password)
