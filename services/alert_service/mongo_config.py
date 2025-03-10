import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

if os.environ.get("PYTEST_RUNNING", ""):
    MONGO_URI = os.getenv("TEST_MONGO_URI", "mongodb://admin:password@mongo:27017/moniflow_test?authSource=admin")
    MONGO_DB_NAME = os.getenv("TEST_MONGO_DB_NAME", "moniflow_test")

mongo_client = MongoClient(MONGO_URI)
# mongo_db_name = mongo_client[MONGO_DB_NAME]
