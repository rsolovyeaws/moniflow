from datetime import datetime
import pytest
import time
import redis
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app
from dao.redis.metrics import RedisMetrics

client = TestClient(app)


@pytest.fixture
def mock_redis():
    """Fixture to mock the Redis client."""
    with patch("redis.client.Redis", autospec=True) as mock_redis_class:
        mock_instance = mock_redis_class.return_value
        yield mock_instance  # Ensure it passes isinstance(redis_client, Redis)


def test_store_metric_in_cache(mock_redis):
    """Test storing a metric in Redis directly using store_metric_in_cache function."""
    metric = {
        "measurement": "cpu",
        "tags": {"host": "server-1"},
        "fields": {"usage": 90.3},
        "timestamp": "2025-02-26T12:00:00Z",
    }

    redis_metrics = RedisMetrics(mock_redis)
    redis_metrics.store_metric_in_cache(metric)

    # Generate expected Redis key
    redis_key = "moniflow:metrics:cpu:host=server-1:usage"

    # Convert timestamp to expected UNIX format
    expected_timestamp = int(time.mktime(time.strptime(metric["timestamp"], "%Y-%m-%dT%H:%M:%SZ")))

    # Assert that Redis ZADD was called correctly
    mock_redis.zadd.assert_called_once_with(redis_key, {90.3: expected_timestamp})


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {
            "tags": {"host": "server-1"},
            "fields": {"usage": 90.3},
            "timestamp": "2025-02-26T12:00:00Z",
        },  # Missing measurement
        {"measurement": "cpu", "fields": {"usage": 90.3}, "timestamp": "2025-02-26T12:00:00Z"},  # Missing tags
        {"measurement": "cpu", "tags": {"host": "server-1"}, "timestamp": "2025-02-26T12:00:00Z"},  # Missing fields
        {
            "measurement": "cpu",
            "tags": {},
            "fields": {"usage": 90.3},
            "timestamp": "2025-02-26T12:00:00Z",
        },  # Empty tags
        {
            "measurement": "cpu",
            "tags": {"host": "server-1"},
            "fields": {},
            "timestamp": "2025-02-26T12:00:00Z",
        },  # Empty fields
    ],
)
def test_store_metric_invalid_payload(invalid_payload):
    """Test the endpoint with invalid payloads (missing required fields)."""
    response = client.post("/metrics/", json=invalid_payload)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {
            "measurement": "cpu",
            "tags": {"host": "server-1"},
            "fields": {"usage": "high"},
            "timestamp": "2025-02-26T12:00:00Z",
        },  # Invalid field type
        {
            "measurement": "cpu",
            "tags": "server-1",
            "fields": {"usage": 90.3},
            "timestamp": "2025-02-26T12:00:00Z",
        },  # Invalid tags type
        {
            "measurement": "cpu",
            "tags": {"host": "server-1"},
            "fields": {"usage": 90.3},
            "timestamp": 1234567890,
        },  # Invalid timestamp type
    ],
)
def test_store_metric_invalid_types(invalid_payload):
    """Test that the API rejects incorrect data types."""
    response = client.post("/metrics/", json=invalid_payload)
    assert response.status_code == 422


def test_store_metric_missing_timestamp(mock_redis):
    """Test storing a metric without a timestamp (should default to current UTC time with 'Z')."""
    metric = {
        "measurement": "cpu",
        "tags": {"host": "server-1"},
        "fields": {"usage": 90.3},
    }

    redis_metrics = RedisMetrics(mock_redis)
    redis_metrics.store_metric_in_cache(metric)

    # Extract the stored timestamp argument passed to Redis
    stored_metric = mock_redis.zadd.call_args[0][1]  # Extract timestamp from mock call
    stored_timestamp = list(stored_metric.values())[0]  # Extract actual timestamp value

    # Ensure timestamp is **recent** (max 5s drift)
    current_time = int(datetime.now().timestamp())
    assert current_time - 5 <= stored_timestamp <= current_time + 5


def test_store_metric_redis_failure():
    """Test Redis failure handling when storing metrics."""

    metric = {
        "measurement": "cpu",
        "tags": {"host": "server-1"},
        "fields": {"usage": 90.3},
        "timestamp": "2025-02-26T12:00:00Z",
    }

    with patch("dao.redis.metrics.RedisMetrics.store_metric_in_cache", side_effect=redis.RedisError("Redis error")):
        response = client.post("/metrics/", json=metric)

    assert response.status_code == 503
    assert response.json() == {"detail": "Redis is unavailable. Metric not cached."}
