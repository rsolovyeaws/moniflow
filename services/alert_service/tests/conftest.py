import os
import pytest
from pymongo import MongoClient
from fastapi.testclient import TestClient
import redis
from main import app
from dotenv import load_dotenv

load_dotenv(".env.test")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:password@mongo:27017/moniflow_test")
TEST_DB_NAME = "moniflow_test"


@pytest.fixture(scope="session")
def test_db():
    """Creates a fresh test database and drops it after tests."""
    client = MongoClient(MONGO_URI)

    # Create the test database
    db = client[TEST_DB_NAME]

    # Yield control to tests
    yield db

    # Cleanup: Drop the test database after all tests
    client.drop_database(TEST_DB_NAME)
    client.close()


@pytest.fixture(autouse=True)
def clear_database(test_db):
    """Clears all collections before each test."""
    for collection in test_db.list_collection_names():
        test_db[collection].delete_many({})


@pytest.fixture(scope="session")
def test_client():
    """Provides a FastAPI test client."""
    return TestClient(app)


@pytest.fixture(scope="function")
def test_redis():
    """Fixture to connect to test Redis and clear it before each test."""
    redis_client = redis.Redis(
        host=os.getenv("TEST_REDIS_HOST", "localhost"),
        port=int(os.getenv("TEST_REDIS_PORT", 6380)),
        db=int(os.getenv("TEST_REDIS_DB", 1)),
        password=os.getenv("TEST_REDIS_PASSWORD", "testpassword"),
        decode_responses=True,
    )
    redis_client.flushdb()
    yield redis_client
    redis_client.flushdb()
