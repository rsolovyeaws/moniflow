import pytest
import redis
from unittest.mock import MagicMock
from dao.redis.metrics import RedisMetrics
from dao.redis.key_schema import KeySchema  # Assuming KeySchema is in key_schema.py


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
    "metric_name, tags, field_name, duration_value, duration_unit",
    [
        ("cpu_usage", {"host": "server-1"}, "usage", 5, "minutes"),
        ("memory_usage", {"region": "us-east"}, "consumption", 10, "seconds"),
    ],
)
def test_get_metric_values_valid_inputs(redis_metrics, metric_name, tags, field_name, duration_value, duration_unit):
    """Test that valid inputs query Redis properly."""
    mock_redis_key = f"moniflow:metrics:{metric_name}:{tags}:{field_name}"

    # Mock Redis response
    redis_metrics.redis_client.zrangebyscore.return_value = ["10.5", "20.1", "30.7"]

    # Mock key generation
    redis_metrics.key_schema.build_redis_metric_key.return_value = mock_redis_key

    values = redis_metrics.get_metric_values(metric_name, tags, field_name, duration_value, duration_unit)

    assert isinstance(values, list)
    assert values == [10.5, 20.1, 30.7]

    # Ensure the key generation method was called correctly
    redis_metrics.key_schema.build_redis_metric_key.assert_called_once_with(metric_name, tags, field_name)

    # Ensure Redis query was made using the generated key
    redis_metrics.redis_client.zrangebyscore.assert_called_once()


@pytest.mark.parametrize(
    "metric_name, tags, field_name, duration_value, duration_unit, expected_error",
    [
        (None, {"host": "server-1"}, "usage", 5, "minutes", "Invalid metric_name: must be a non-empty string."),
        ("", {"host": "server-1"}, "usage", 5, "minutes", "Invalid metric_name: must be a non-empty string."),
        ("valid_metric", None, "usage", 5, "minutes", "Invalid tags: must be a non-empty dictionary."),
        ("valid_metric", {}, "usage", 5, "minutes", "Invalid tags: must be a non-empty dictionary."),
        ("valid_metric", {"host": "server-1"}, None, 5, "minutes", "Invalid field_name: must be a non-empty string."),
        (
            "valid_metric",
            {"host": "server-1"},
            "usage",
            -1,
            "minutes",
            "Invalid duration_value: must be a positive integer.",
        ),
        (
            "valid_metric",
            {"host": "server-1"},
            "usage",
            5,
            "invalid_unit",
            "Invalid duration_unit: must be one of 'seconds', 'minutes', or 'hours'.",
        ),
    ],
)
def test_get_metric_values_invalid_inputs(
    redis_metrics, metric_name, tags, field_name, duration_value, duration_unit, expected_error
):
    """Ensure that invalid inputs raise ValueErrors."""
    with pytest.raises(ValueError, match=expected_error):
        redis_metrics.get_metric_values(metric_name, tags, field_name, duration_value, duration_unit)


def test_get_metric_values_redis_error(redis_metrics):
    """Ensure Redis errors are handled gracefully and return an empty list."""
    mock_redis_key = "moniflow:metrics:cpu_usage:host=server-1:usage"

    # Mock key generation
    redis_metrics.key_schema.build_redis_metric_key.return_value = mock_redis_key

    # Simulate Redis failure
    redis_metrics.redis_client.zrangebyscore.side_effect = redis.RedisError("Redis failure")

    values = redis_metrics.get_metric_values("cpu_usage", {"host": "server-1"}, "usage", 5, "minutes")

    assert values == []

    # Ensure Redis query was attempted
    redis_metrics.redis_client.zrangebyscore.assert_called_once()
