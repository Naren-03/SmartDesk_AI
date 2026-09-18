from contextlib import asynccontextmanager

from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

from core.config import settings
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


app.include_router(user_router, prefix="/api/v1/users", tags=["users"])


@app.get("/safe")
def safe_endpoint():
    return {"message": "This is a safe endpoint."}
