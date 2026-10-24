import asyncio

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

from core.errors import ErrorResponse, get_error_code
from main import http_exception_handler, validation_exception_handler


def test_http_error_response_has_stable_code_and_message():
    response = asyncio.run(
        http_exception_handler(
            None,
            HTTPException(status_code=401, detail="Invalid email or password"),
        )
    )

    assert response.status_code == 401
    assert response.body == (
        b'{"code":"INVALID_CREDENTIALS",'
        b'"message":"Invalid email or password","details":null}'
    )


def test_validation_error_response_has_details():
    validation_error = RequestValidationError(
        [
            {
                "type": "string_too_short",
                "loc": ("body", "password"),
                "msg": "String should have at least 8 characters",
                "input": "short",
            }
        ]
    )

    response = asyncio.run(validation_exception_handler(None, validation_error))

    assert response.status_code == 422
    assert response.body.startswith(
        b'{"code":"VALIDATION_ERROR","message":"Request validation failed",'
    )
    assert b'"password"' in response.body


def test_unknown_error_message_uses_status_code_fallback():
    assert get_error_code(418, "Teapot") == "API_ERROR"
    assert ErrorResponse(code="API_ERROR", message="Teapot").model_dump() == {
        "code": "API_ERROR",
        "message": "Teapot",
        "details": None,
    }
