from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient

from core.config import settings
from core.errors import ErrorResponse, get_error_code
from routes.api.v1.users import router as user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = AsyncIOMotorClient(settings.mongo_uri)
    app.state.mongo_client = client
    app.state.db = client[settings.mongo_db]
    await app.state.db.users.create_index("email", unique=True)
    yield
    client.close()


app = FastAPI(lifespan=lifespan)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    details = None if isinstance(exc.detail, str) else exc.detail
    error = ErrorResponse(
        code=get_error_code(exc.status_code, message),
        message=message,
        details=details,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error.model_dump(),
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error = ErrorResponse(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details=jsonable_encoder(exc.errors()),
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error.model_dump(),
    )


app.include_router(user_router, prefix="/api/v1/users")


@app.get("/safe")
def safe_endpoint():
    return {"message": "This is a safe endpoint."}
