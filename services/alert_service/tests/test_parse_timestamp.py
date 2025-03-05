import pytest
from dao.redis.metrics import RedisMetrics


@pytest.mark.parametrize(
    "input_timestamp, expected_unix",
    [
        # Standard ISO format (UTC, explicit Z)
        ("2025-02-26T12:00:00Z", 1740571200),
        # ISO format with microseconds and explicit UTC (Z)
        ("2025-02-26T12:00:00.123456Z", 1740571200),
        # ISO format with different timezone offsets (converted to UTC)
        ("2025-02-26T14:00:00+02:00", 1740571200),  # UTC equivalent
        ("2025-02-26T10:00:00-02:00", 1740571200),  # UTC equivalent
        ("2025-02-26T09:30:00-02:30", 1740571200),  # UTC equivalent
    ],
)
def test_parse_timestamp_valid_formats(input_timestamp, expected_unix):
    """Test parse_timestamp with valid strict ISO 8601 formats (explicit time zones required)."""
    result = RedisMetrics.parse_timestamp(input_timestamp)
    assert isinstance(result, int)
    assert result == expected_unix


@pytest.mark.parametrize(
    "invalid_input, error_msg",
    [
        # Completely invalid formats
        ("not-a-timestamp", "Invalid timestamp format"),
        ("2025-02-26", "Invalid timestamp format"),  # Missing time & timezone
        ("2025-02-26 12:00:00", "Invalid timestamp format"),  # Missing `T`
        ("2025-02-26T12:00:00", "Invalid timestamp format: 2025-02-26T12:00:00"),  # Missing timezone
        # Wrong date/time structure
        ("2025/02/26T12:00:00Z", "Invalid timestamp format"),  # Wrong separator (/)
        ("2025-02-26T25:00:00Z", "Invalid timestamp format"),  # Invalid hour
        ("2025-13-26T12:00:00Z", "Invalid timestamp format"),  # Invalid month
        ("2025-02-30T12:00:00Z", "Invalid timestamp format"),  # Invalid day
        # Wrong types
        (None, "Invalid timestamp format"),
        ({}, "Invalid timestamp format"),
        ([], "Invalid timestamp format"),
        (True, "Invalid timestamp format"),
        (
            1645555200,
            "Invalid timestamp format: Unix timestamps are not accepted directly",
        ),  # Unix timestamp not allowed
    ],
)
def test_parse_timestamp_invalid_formats(invalid_input, error_msg):
    """Test parse_timestamp with invalid timestamps that should raise ValueError."""
    with pytest.raises(ValueError) as exc_info:
        RedisMetrics.parse_timestamp(invalid_input)
    assert error_msg in str(exc_info.value)


def test_parse_timestamp_timezone_consistency():
    """Test that different timezone representations of the same time return consistent Unix timestamps."""
    utc_time = "2025-02-26T12:00:00Z"
    plus_two = "2025-02-26T14:00:00+02:00"
    minus_two = "2025-02-26T10:00:00-02:00"

    utc_result = RedisMetrics.parse_timestamp(utc_time)
    plus_result = RedisMetrics.parse_timestamp(plus_two)
    minus_result = RedisMetrics.parse_timestamp(minus_two)

    assert utc_result == plus_result == minus_result


def test_parse_timestamp_preserves_type():
    """Ensure parse_timestamp always returns an integer."""
    utc_time = "2025-02-26T12:00:00Z"
    result = RedisMetrics.parse_timestamp(utc_time)
    assert isinstance(result, int)
