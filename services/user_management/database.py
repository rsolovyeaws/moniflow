import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:password@mongo:27017")
DB_NAME = "moniflow"

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

# Users collection
users_collection = db["users"]