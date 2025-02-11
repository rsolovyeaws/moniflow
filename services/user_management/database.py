import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from passlib.context import CryptContext

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

DEFAULT_ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:password@mongo:27017")
DB_NAME = "moniflow"

try:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    users_collection = db["users"]
    logger.info("Successfully connected to MongoDB")
except Exception as e:
    logger.error(f"MongoDB Connection Error: {e}")
    users_collection = None
    

async def create_admin_user():
    """Creates an admin user if none exists in the database."""
    if users_collection is None:
        logger.error("Database connection not established.")
        return

    existing_admin = await users_collection.find_one({"role": "admin"})
    if not existing_admin:
        admin_data = {
            "username": DEFAULT_ADMIN_USERNAME,
            "hashed_password": pwd_context.hash(DEFAULT_ADMIN_PASSWORD),
            "role": "admin"
        }
        await users_collection.insert_one(admin_data)
        logger.info(f"Admin user created with username: {DEFAULT_ADMIN_USERNAME}")
    else:
        logger.info("Admin user already exists.")

async def store_refresh_token(username: str, refresh_token: str):
    await users_collection.update_one({"username": username}, {"$set": {"refresh_token": refresh_token}})   

async def get_refresh_token(username: str):
    user = await users_collection.find_one({"username": username}, {"refresh_token": 1})
    return user.get("refresh_token", None) if user else None

async def revoke_refresh_token(username: str):
    await users_collection.update_one({"username": username}, {"$unset": {"refresh_token": ""}})
