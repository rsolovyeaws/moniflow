import pytest
from redis_key_schema import KeySchema


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
