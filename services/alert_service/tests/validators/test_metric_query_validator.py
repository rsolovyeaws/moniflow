import pytest
from validators.metric_query_validator import MetricQueryValidator


@pytest.mark.parametrize(
    "metric_name, tags, field_name, duration",
    [
        ("cpu_usage", {"host": "server-1"}, "usage", 300),  # 5 minutes in seconds
        ("memory_usage", {"region": "us-east"}, "consumption", 10),  # 10 seconds
    ],
)
def test_valid_inputs(metric_name, tags, field_name, duration):
    """Test that valid inputs pass validation without raising errors."""
    MetricQueryValidator.validate(metric_name, tags, field_name, duration)


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
def test_invalid_inputs(metric_name, tags, field_name, duration, expected_error):
    """Ensure that invalid inputs raise ValueErrors with correct messages."""
    with pytest.raises(ValueError, match=expected_error):
        MetricQueryValidator.validate(metric_name, tags, field_name, duration)
