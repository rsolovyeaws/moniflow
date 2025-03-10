import pytest
import redis
from unittest.mock import MagicMock
from dao.redis.metrics import RedisMetrics
from dao.redis.key_schema import KeySchema


@pytest.fixture
def mock_redis():
    """Fixture to create a mock Redis client."""
    return MagicMock(spec=redis.Redis)


@pytest.fixture
def mock_key_schema():
    """Fixture to mock KeySchema."""
    return MagicMock(spec=KeySchema)


@pytest.fixture
def redis_metrics(mock_redis, mock_key_schema):
    """Fixture to create a RedisMetrics instance with mocked dependencies."""
    return RedisMetrics(mock_redis, mock_key_schema)


@pytest.mark.parametrize(
    "metric_name, tags, field_name, duration",
    [
        ("cpu_usage", {"host": "server-1"}, "usage", 300),  # 5 minutes in seconds
        ("memory_usage", {"region": "us-east"}, "consumption", 10),  # 10 seconds
    ],
)
def test_get_metric_values_valid_inputs(redis_metrics, metric_name, tags, field_name, duration):
    """Test that valid inputs query Redis properly."""
    mock_redis_key = f"moniflow:metrics:{metric_name}:{tags}:{field_name}"

    # Mock Redis response
    redis_metrics.redis_client.zrangebyscore.return_value = ["10.5", "20.1", "30.7"]

    # Mock key generation
    redis_metrics.key_schema.build_redis_metric_key.return_value = mock_redis_key

    values = redis_metrics.get_metric_values(metric_name, tags, field_name, duration)

    assert isinstance(values, list)
    assert values == [10.5, 20.1, 30.7]

    # Ensure the key generation method was called correctly
    redis_metrics.key_schema.build_redis_metric_key.assert_called_once_with(metric_name, tags, field_name)

    # Ensure Redis query was made using the generated key
    redis_metrics.redis_client.zrangebyscore.assert_called_once()


@pytest.mark.parametrize(
    "metric_name, tags, field_name, duration, expected_error",
    [
        (None, {"host": "server-1"}, "usage", 300, "Invalid metric_name: must be a non-empty string."),
        ("", {"host": "server-1"}, "usage", 300, "Invalid metric_name: must be a non-empty string."),
        ("valid_metric", None, "usage", 300, "Invalid tags: must be a non-empty dictionary."),
        ("valid_metric", {}, "usage", 300, "Invalid tags: must be a non-empty dictionary."),
        ("valid_metric", {"host": "server-1"}, None, 300, "Invalid field_name: must be a non-empty string."),
        ("valid_metric", {"host": "server-1"}, "usage", -1, "Invalid duration_value: must be a positive integer."),
        ("valid_metric", {"host": "server-1"}, "usage", "five", "Invalid duration_value: must be a positive integer."),
    ],
)
def test_get_metric_values_invalid_inputs(redis_metrics, metric_name, tags, field_name, duration, expected_error):
    """Ensure that invalid inputs raise ValueErrors with correct messages."""
    with pytest.raises(ValueError, match=expected_error):
        redis_metrics.get_metric_values(metric_name, tags, field_name, duration)


def test_get_metric_values_redis_error(redis_metrics):
    """Ensure Redis errors are handled gracefully and return an empty list."""
    mock_redis_key = "moniflow:metrics:cpu_usage:host=server-1:usage"

    # Mock key generation
    redis_metrics.key_schema.build_redis_metric_key.return_value = mock_redis_key

    # Simulate Redis failure
    redis_metrics.redis_client.zrangebyscore.side_effect = redis.RedisError("Redis failure")

    values = redis_metrics.get_metric_values("cpu_usage", {"host": "server-1"}, "usage", 300)

    assert values == []

    # Ensure Redis query was attempted
    redis_metrics.redis_client.zrangebyscore.assert_called_once()
