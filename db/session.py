from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.database import Database
from dotenv import load_dotenv
import os

load_dotenv()


MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "mydatabase")


client: AsyncIOMotorClient = AsyncIOMotorClient(MONGO_URI)
db: Database = client[MONGO_DB]