import json
import pytest
from fastapi.testclient import TestClient
import redis
from main import app
from redis_handler import store_metric_in_cache
from datetime import datetime, timezone
from unittest.mock import patch


client = TestClient(app)


def test_store_metric_in_redis(test_redis):
    """Test storing a metric in Redis."""
    metric = {
        "measurement": "cpu",
        "tags": {"host": "server-1"},
        "fields": {"usage": 90.3},
        "timestamp": "2025-02-26T12:00:00Z",
    }

    response = client.post("/metrics/", json=metric)
    assert response.status_code == 200
    assert response.json() == {"message": "Metric cached"}

    # Check if metric is stored in Redis
    redis_data = test_redis.lrange("moniflow:metrics", 0, -1)
    assert len(redis_data) == 1
    assert json.loads(redis_data[0]) == metric


def test_store_metric_in_cache(test_redis):
    """Test storing a metric in Redis directly using store_metric_in_cache function."""
    metric = {
        "measurement": "cpu",
        "tags": {"host": "server-1"},
        "fields": {"usage": 90.3},
        "timestamp": "2025-02-26T12:00:00Z",
    }

    # Call the function that should store data in Redis
    store_metric_in_cache(metric)

    # Retrieve the stored data from Redis
    redis_data = test_redis.lrange("moniflow:metrics", 0, -1)

    assert len(redis_data) == 1  # Ensure that one metric was stored
    assert json.loads(redis_data[0]) == metric  # Ensure stored metric matches


@pytest.mark.parametrize(
    "invalid_payload",
    [
        # Missing "measurement"
        {
            "tags": {"host": "server-1"},
            "fields": {"usage": 90.3},
            "timestamp": "2025-02-26T12:00:00Z",
        },
        # Missing "tags"
        {
            "measurement": "cpu",
            "fields": {"usage": 90.3},
            "timestamp": "2025-02-26T12:00:00Z",
        },
        # Missing "fields"
        {
            "measurement": "cpu",
            "tags": {"host": "server-1"},
            "timestamp": "2025-02-26T12:00:00Z",
        },
        # Empty "tags"
        {
            "measurement": "cpu",
            "tags": {},
            "fields": {"usage": 90.3},
            "timestamp": "2025-02-26T12:00:00Z",
        },
        # Empty "fields"
        {
            "measurement": "cpu",
            "tags": {"host": "server-1"},
            "fields": {},
            "timestamp": "2025-02-26T12:00:00Z",
        },
    ],
)
def test_store_metric_invalid_payload(invalid_payload):
    """Test the endpoint with invalid payloads (missing required fields)."""
    response = client.post("/metrics/", json=invalid_payload)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "invalid_payload",
    [
        # "fields" values should be float, but here it's a string
        {
            "measurement": "cpu",
            "tags": {"host": "server-1"},
            "fields": {"usage": "high"},
            "timestamp": "2025-02-26T12:00:00Z",
        },
        # "tags" should be a dictionary, but here it's a string
        {
            "measurement": "cpu",
            "tags": "server-1",
            "fields": {"usage": 90.3},
            "timestamp": "2025-02-26T12:00:00Z",
        },
        # "timestamp" should be a string (ISO format), but here it's an integer
        {
            "measurement": "cpu",
            "tags": {"host": "server-1"},
            "fields": {"usage": 90.3},
            "timestamp": 1234567890,
        },
    ],
)
def test_store_metric_invalid_types(invalid_payload):
    """Test that the API rejects incorrect data types."""
    response = client.post("/metrics/", json=invalid_payload)
    assert response.status_code == 422


def test_store_metric_missing_timestamp(test_redis):
    """Test storing a metric without a timestamp (should default to current time)."""
    metric = {
        "measurement": "cpu",
        "tags": {"host": "server-1"},
        "fields": {"usage": 90.3},
    }

    response = client.post("/metrics/", json=metric)
    assert response.status_code == 200
    assert response.json() == {"message": "Metric cached"}

    # Retrieve the stored metric from Redis
    redis_data = test_redis.lrange("moniflow:metrics", 0, -1)
    assert len(redis_data) == 1

    stored_metric = json.loads(redis_data[0])
    assert "timestamp" in stored_metric  # Ensure timestamp was added
    assert stored_metric["measurement"] == metric["measurement"]
    assert stored_metric["tags"] == metric["tags"]
    assert stored_metric["fields"] == metric["fields"]

    # Ensure timestamp is close to now
    now = datetime.now(timezone.utc).isoformat()
    assert (
        stored_metric["timestamp"][:16] == now[:16]
    )  # Compare up to minutes to avoid millisecond mismatch


def test_store_metric_redis_failure():
    """Test Redis failure handling when storing metrics."""

    metric = {
        "measurement": "cpu",
        "tags": {"host": "server-1"},
        "fields": {"usage": 90.3},
        "timestamp": "2025-02-26T12:00:00Z",
    }
    # might need to change if testing outside of the docker container
    with patch(
        "main.store_metric_in_cache",
        side_effect=redis.RedisError("Redis error"),
    ):
        response = client.post("/metrics/", json=metric)

    assert response.status_code == 503
    assert response.json() == {"detail": "Redis is unavailable. Metric not cached."}
