import pytest
from validators.metric_query_validator import MetricQueryValidator


@pytest.mark.parametrize(
    "metric_name, tags, field_name, duration_value, duration_unit",
    [
        ("cpu_usage", {"host": "server-1"}, "usage", 5, "minutes"),
        ("memory_usage", {"region": "us-east"}, "consumption", 10, "seconds"),
    ],
)
def test_valid_inputs(metric_name, tags, field_name, duration_value, duration_unit):
    """Test that valid inputs pass validation without raising errors."""
    MetricQueryValidator.validate(metric_name, tags, field_name, duration_value, duration_unit)


@pytest.mark.parametrize(
    "metric_name, tags, field_name, duration_value, duration_unit, expected_error",
    [
        (None, {"host": "server-1"}, "usage", 5, "minutes", "Invalid metric_name: must be a non-empty string."),
        ("", {"host": "server-1"}, "usage", 5, "minutes", "Invalid metric_name: must be a non-empty string."),
        ("valid_metric", None, "usage", 5, "minutes", "Invalid tags: must be a non-empty dictionary."),
        ("valid_metric", {}, "usage", 5, "minutes", "Invalid tags: must be a non-empty dictionary."),
        ("valid_metric", {"host": "server-1"}, None, 5, "minutes", "Invalid field_name: must be a non-empty string."),
        ("valid_metric", {"host": "server-1"}, "usage", -1, "minutes", "Invalid duration_value: must be a positive integer."),
        ("valid_metric", {"host": "server-1"}, "usage", 5, "invalid_unit", "Invalid duration_unit: must be one of 'seconds', 'minutes', or 'hours'."),
    ],
)
def test_invalid_inputs(metric_name, tags, field_name, duration_value, duration_unit, expected_error):
    """Ensure that invalid inputs raise ValueErrors with correct messages."""
    with pytest.raises(ValueError, match=expected_error):
        MetricQueryValidator.validate(metric_name, tags, field_name, duration_value, duration_unit)
