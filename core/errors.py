from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Any | None = None


_ERROR_CODES = {
    "Not authenticated": "AUTHENTICATION_REQUIRED",
    "Could not validate credentials": "INVALID_CREDENTIALS",
    "Invalid email or password": "INVALID_CREDENTIALS",
    "Email already registered": "EMAIL_ALREADY_REGISTERED",
    "User not found": "USER_NOT_FOUND",
    "Insufficient permissions": "FORBIDDEN",
    "User account is inactive": "ACCOUNT_INACTIVE",
    "Administrators cannot deactivate their own account": "SELF_DEACTIVATION_NOT_ALLOWED",
}

_STATUS_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    500: "INTERNAL_SERVER_ERROR",
}


def get_error_code(status_code: int, message: str) -> str:
    return _ERROR_CODES.get(message, _STATUS_CODES.get(status_code, "API_ERROR"))
