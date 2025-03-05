import pytest
import redis
from unittest.mock import MagicMock
from dao.redis.metrics import RedisMetrics


@pytest.fixture
def mock_redis():
    """Fixture to create a mock Redis client."""
    return MagicMock(spec=redis.Redis)


@pytest.fixture
def redis_metrics(mock_redis):
    """Fixture to create a RedisMetrics instance with a mock Redis client."""
    return RedisMetrics(mock_redis)


# Test Initialization
def test_redis_metrics_initialization(mock_redis):
    """Ensure RedisMetrics initializes with a valid Redis client."""
    instance = RedisMetrics(mock_redis)
    assert instance.redis_client == mock_redis


def test_redis_metrics_initialization_invalid():
    """Ensure RedisMetrics raises TypeError if initialized with an invalid client."""
    with pytest.raises(TypeError, match="redis_client must be an instance of redis.Redis"):
        RedisMetrics("not-a-redis-client")


# Test `_convert_duration_to_seconds`
@pytest.mark.parametrize(
    "value, unit, expected_seconds",
    [
        (1, "seconds", 1),
        (5, "seconds", 5),
        (1, "minutes", 60),
        (3, "minutes", 180),
        (1, "hours", 3600),
        (2, "hours", 7200),
    ],
)
def test_convert_duration_to_seconds(value, unit, expected_seconds):
    """Test conversion of different time units to seconds."""
    assert RedisMetrics._convert_duration_to_seconds(value, unit) == expected_seconds


def test_convert_duration_to_seconds_invalid_unit():
    """Ensure invalid time units raise a ValueError."""
    with pytest.raises(ValueError, match="Invalid duration unit: days. Must be 'seconds', 'minutes', or 'hours'."):
        RedisMetrics._convert_duration_to_seconds(5, "days")


@pytest.mark.parametrize(
    "redis_key, duration_value, duration_unit",
    [
        ("moniflow:metrics:cpu_usage:host=server-1:usage", 5, "minutes"),
        ("moniflow:metrics:memory_usage:region=us-east:consumption", 10, "seconds"),
    ],
)
def test_get_metric_values_valid_inputs(redis_metrics, redis_key, duration_value, duration_unit):
    """Test that valid inputs query Redis properly."""
    redis_metrics.redis_client.zrangebyscore.return_value = ["10.5", "20.1", "30.7"]

    values = redis_metrics.get_metric_values(redis_key, duration_value, duration_unit)

    assert isinstance(values, list)
    assert values == [10.5, 20.1, 30.7]
    redis_metrics.redis_client.zrangebyscore.assert_called_once()


@pytest.mark.parametrize(
    "redis_key, duration_value, duration_unit, expected_error",
    [
        (None, 5, "minutes", "Invalid redis_key: must be a non-empty string."),
        ("", 5, "minutes", "Invalid redis_key: must be a non-empty string."),
        ("valid_key", -1, "minutes", "Invalid duration_value: must be a positive integer."),
        ("valid_key", "five", "minutes", "Invalid duration_value: must be a positive integer."),
        ("valid_key", 5, "invalid_unit", "Invalid duration_unit: must be 'seconds', 'minutes', or 'hours'."),
    ],
)
def test_get_metric_values_invalid_inputs(redis_metrics, redis_key, duration_value, duration_unit, expected_error):
    """Ensure that invalid inputs raise ValueErrors."""
    with pytest.raises(ValueError, match=expected_error):
        redis_metrics.get_metric_values(redis_key, duration_value, duration_unit)


def test_get_metric_values_redis_error(redis_metrics):
    """Ensure Redis errors are handled gracefully and return an empty list."""
    redis_metrics.redis_client.zrangebyscore.side_effect = redis.RedisError("Redis failure")

    values = redis_metrics.get_metric_values("valid_key", 5, "minutes")

    assert values == []
    redis_metrics.redis_client.zrangebyscore.assert_called_once()
