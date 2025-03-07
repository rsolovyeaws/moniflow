import pytest
from dao.redis.key_schema import KeySchema


@pytest.mark.parametrize(
    "metric_name, tags, field_name, expected_key",
    [
        # Basic valid input
        ("cpu_usage", {"host": "server-1"}, "usage", "moniflow:metrics:cpu_usage:host=server-1:usage"),
        # Multiple tags (unordered input)
        (
            "cpu_usage",
            {"group": "alpha", "host": "server-1"},
            "usage",
            "moniflow:metrics:cpu_usage:group=alpha,host=server-1:usage",
        ),
        # Single tag
        (
            "memory_usage",
            {"region": "us-east"},
            "consumption",
            "moniflow:metrics:memory_usage:region=us-east:consumption",
        ),
        # Tags with special characters
        (
            "disk_io",
            {"disk": "/dev/sda1", "mode": "rw"},
            "throughput",
            "moniflow:metrics:disk_io:disk=/dev/sda1,mode=rw:throughput",
        ),
        # Unicode characters in tags
        ("cpu_usage", {"server": "日本"}, "temperature", "moniflow:metrics:cpu_usage:server=日本:temperature"),
        # Extremely long strings
        ("x" * 100, {"longtag": "y" * 100}, "z" * 100, f"moniflow:metrics:{'x' * 100}:longtag={'y' * 100}:{'z' * 100}"),
    ],
)
def test_build_redis_metric_key(metric_name, tags, field_name, expected_key):
    """Test Redis key generation for valid inputs."""
    assert KeySchema.build_redis_metric_key(metric_name, tags, field_name) == expected_key


@pytest.mark.parametrize(
    "rule_id, expected_key",
    [
        # Basic rule ID
        ("rule123", "moniflow:alert_state:rule123"),
        # Rule ID with special characters
        ("alert/cpu-high#2", "moniflow:alert_state:alert/cpu-high#2"),
        # Long rule ID
        ("a" * 100, f"moniflow:alert_state:{'a' * 100}"),
        # Empty rule ID
        ("", "moniflow:alert_state:"),
    ],
)
def test_build_alert_state_key(rule_id, expected_key):
    """Test alert state key generation for various rule IDs."""
    assert KeySchema.build_alert_state_key(rule_id) == expected_key


@pytest.mark.parametrize(
    "rule_id, expected_key",
    [
        # Basic rule ID
        ("rule123", "moniflow:recovery_state:rule123"),
        # Rule ID with special characters
        ("recovery/mem-low#2", "moniflow:recovery_state:recovery/mem-low#2"),
        # Long rule ID
        ("b" * 100, f"moniflow:recovery_state:{'b' * 100}"),
        # Empty rule ID
        ("", "moniflow:recovery_state:"),
    ],
)
def test_build_recovery_state_key(rule_id, expected_key):
    """Test recovery state key generation for various rule IDs."""
    assert KeySchema.build_recovery_state_key(rule_id) == expected_key
