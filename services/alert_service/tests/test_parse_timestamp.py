import pytest
from datetime import datetime
from redis_handler import parse_timestamp


@pytest.mark.parametrize(
    "input_timestamp, expected_unix",
    [
        # Already Unix timestamp
        (1645555200, 1645555200),
        # Standard ISO format without microseconds/timezone
        ("2022-02-22T12:00:00Z", 1645531200),
        # ISO format with microseconds and timezone
        ("2022-02-22T12:00:00.123456+00:00", 1645531200),
        # ISO format with different timezone offsets
        ("2022-02-22T14:00:00+02:00", 1645531200),  # Same time, different zone
        ("2022-02-22T10:00:00-02:00", 1645531200),  # Same time, different zone
        # Current time (testing with small delta)
        (int(datetime.now().timestamp()), int(datetime.now().timestamp())),
    ],
)
def test_parse_timestamp_valid_formats(input_timestamp, expected_unix):
    """Test parse_timestamp with various valid timestamp formats."""
    result = parse_timestamp(input_timestamp)
    assert isinstance(result, int)
    assert result == expected_unix


@pytest.mark.parametrize(
    "invalid_input",
    [
        "invalid-timestamp",
        "2022/02/22 12:00:00",
        "2022-02-22",
        "",
        None,
        "2022-02-22T25:00:00Z",  # Invalid hour
        "2022-13-22T12:00:00Z",  # Invalid month
        "not-a-timestamp",
        "2022-02-22 12:00:00",  # Missing T and Z
        "2022-02-22T12:00:00",  # Missing Z
        {},  # Wrong type
        [],  # Wrong type
        True,  # Wrong type
    ],
)
def test_parse_timestamp_invalid_formats(invalid_input):
    """Test parse_timestamp with invalid timestamp formats."""
    with pytest.raises(ValueError) as exc_info:
        parse_timestamp(invalid_input)
    assert "Invalid timestamp format" in str(exc_info.value)


def test_parse_timestamp_type_preservation():
    """Test that parse_timestamp always returns an integer."""
    current_time = int(datetime.now().timestamp())
    result = parse_timestamp(current_time)
    assert isinstance(result, int)
    assert result == current_time


def test_parse_timestamp_timezone_consistency():
    """Test that different timezone representations of the same time return consistent Unix timestamps."""
    utc_time = "2022-02-22T12:00:00Z"
    plus_two = "2022-02-22T14:00:00+02:00"
    minus_two = "2022-02-22T10:00:00-02:00"

    utc_result = parse_timestamp(utc_time)
    plus_result = parse_timestamp(plus_two)
    minus_result = parse_timestamp(minus_two)

    assert utc_result == plus_result == minus_result
