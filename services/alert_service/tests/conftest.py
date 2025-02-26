import os
import pytest
from pymongo import MongoClient
from fastapi.testclient import TestClient
from main import app

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
