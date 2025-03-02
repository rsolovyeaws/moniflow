import pytest
import time
import redis
from main import app
from fastapi.testclient import TestClient
from redis_handler import store_metric_in_cache
from unittest.mock import patch
from redis_handler import parse_timestamp


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

    # Generate expected Redis key
    redis_key = "moniflow:metrics:cpu:host=server-1:usage"

    # Convert timestamp to expected UNIX format
    expected_timestamp = int(time.mktime(time.strptime(metric["timestamp"], "%Y-%m-%dT%H:%M:%SZ")))

    # Allow for slight variations (±5 seconds)
    min_time = expected_timestamp - 5
    max_time = expected_timestamp + 5

    redis_data = test_redis.zrangebyscore(redis_key, min_time, max_time, withscores=True)

    assert len(redis_data) == 1  # Ensure the metric was stored
    assert float(redis_data[0][0]) == 90.3  # Ensure stored value matches
    assert min_time <= int(redis_data[0][1]) <= max_time  # Ensure timestamp is in range


def test_store_metric_in_cache(test_redis):
    """Test storing a metric in Redis directly using store_metric_in_cache function."""
    metric = {
        "measurement": "cpu",
        "tags": {"host": "server-1"},
        "fields": {"usage": 90.3},
        "timestamp": "2025-02-26T12:00:00Z",
    }

    store_metric_in_cache(metric)

    # Generate expected Redis key
    redis_key = "moniflow:metrics:cpu:host=server-1:usage"

    # Convert timestamp to expected UNIX format
    expected_timestamp = int(time.mktime(time.strptime(metric["timestamp"], "%Y-%m-%dT%H:%M:%SZ")))

    # Allow for slight variations (±5 seconds)
    min_time = expected_timestamp - 5
    max_time = expected_timestamp + 5

    redis_data = test_redis.zrangebyscore(redis_key, min_time, max_time, withscores=True)

    assert len(redis_data) == 1
    assert float(redis_data[0][0]) == 90.3
    assert min_time <= int(redis_data[0][1]) <= max_time


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

    # Generate expected Redis key
    redis_key = "moniflow:metrics:cpu:host=server-1:usage"

    # Retrieve the stored metric from Redis
    current_time = int(time.time())
    redis_data = test_redis.zrangebyscore(redis_key, current_time - 5, current_time + 5, withscores=True)

    assert len(redis_data) == 1  # Ensure one metric was stored
    assert float(redis_data[0][0]) == 90.3  # Value check

    stored_timestamp = int(redis_data[0][1])  # Extract stored timestamp
    assert abs(stored_timestamp - current_time) < 5  # Allow small time drift


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


# @pytest.mark.parametrize(
#     "input_timestamp, expected_unix",
#     [
#         # Standard ISO format without microseconds or timezone
#         ("2025-02-28T12:00:00Z", 1745995200),
#         # ISO format with microseconds and timezone offset
#         ("2025-02-28T12:00:00.123456+00:00", 1745995200),
#         # ISO format with different timezone offset
#         ("2025-02-28T15:00:00.789000+03:00", 1745995200),
#         # ISO format without timezone but with microseconds
#         ("2025-02-28T12:00:00.456789", 1745995200),
#         # Already in Unix timestamp format (int)
#         (1745995200, 1745995200),
#     ],
# )
# def test_parse_timestamp(input_timestamp, expected_unix):
#     """Test that parse_timestamp correctly converts various formats to Unix time."""
#     assert parse_timestamp(input_timestamp) == expected_unix


# def test_parse_timestamp_invalid_format():
#     """Test that parse_timestamp raises ValueError for invalid timestamps."""
#     with pytest.raises(ValueError, match="Invalid timestamp format"):
#         parse_timestamp("invalid-timestamp")

#     with pytest.raises(ValueError, match="Invalid timestamp format"):
#         parse_timestamp("2025/02/28 12:00:00")

#     with pytest.raises(ValueError, match="Invalid timestamp format"):
#         parse_timestamp(None)
