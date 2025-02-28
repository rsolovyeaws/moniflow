import os
import redis
import json
import logging
import time
from dotenv import load_dotenv
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_ALERT_EXPIRY = int(os.getenv("REDIS_ALERT_EXPIRY", "300"))

if os.getenv("PYTEST_RUNNING") == "true":
    logger.info("Running tests, using test Redis configuration")
    load_dotenv(".env.test")
    REDIS_HOST = os.getenv("TEST_REDIS_HOST", "moniflow-test-redis")
    REDIS_PORT = int(os.getenv("TEST_REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("TEST_REDIS_DB", 1))
    REDIS_PASSWORD = os.getenv("TEST_REDIS_PASSWORD", None)
else:
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True,
)


def store_metric_in_cache(metric_data: dict):
    """
    Store incoming metric in Redis with separate keys per field.

    Redis Sorted Set (ZADD) Format:
        moniflow:metrics:{measurement}:{sorted_tags}:{field_name}

    Example:
        moniflow:metrics:cpu_usage:group=alpha:host=server-1:usage
        moniflow:metrics:cpu_usage:group=alpha:host=server-1:temperature

    Args:
        metric_data (dict): The metric data to store.
    """
    try:
        measurement = metric_data.get("measurement")
        tags = metric_data.get("tags", {})
        fields = metric_data.get("fields", {})
        timestamp = metric_data.get("timestamp", datetime.utcnow().isoformat())

        # Convert timestamp to Unix time
        timestamp = parse_timestamp(timestamp)

        # Generate Redis key
        sorted_tags = ":".join(f"{k}={v}" for k, v in sorted(tags.items()))
        for field_name, field_value in fields.items():
            redis_key = f"moniflow:metrics:{measurement}:{sorted_tags}:{field_name}"
            redis_client.zadd(redis_key, {field_value: timestamp})

            logger.info(f"Stored in Redis: {redis_key} -> {field_value} at {timestamp}")

    except redis.RedisError as e:
        logger.error(f"Redis Error: {e}")
        raise


def parse_timestamp(timestamp):
    """Parse a timestamp string into a UNIX timestamp (seconds)."""
    if isinstance(timestamp, bool):  # Handle boolean specifically since bool is a subclass of int
        raise ValueError("Invalid timestamp format: input must be string or integer")

    if isinstance(timestamp, int):  # Already in Unix format
        return timestamp

    if not isinstance(timestamp, str):
        raise ValueError("Invalid timestamp format: input must be string or integer")

    if not timestamp:
        raise ValueError("Invalid timestamp format: empty string")

    # Ensure string has required ISO format parts
    if "T" not in timestamp:
        raise ValueError("Invalid timestamp format: must be ISO 8601 format")

    try:
        # Handle UTC format with "Z"
        if timestamp.endswith("Z"):
            dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
            return int(dt.timestamp())

        # Handle full ISO format with timezone offset (e.g., "+00:00", "-03:00")
        if any(c in timestamp[-6:] for c in ("+", "-")):  # Checks if last 6 chars contain + or -
            dt = datetime.fromisoformat(timestamp)
            return int(dt.timestamp())

        # Explicitly reject timestamps without a timezone
        raise ValueError(f"Invalid timestamp format (missing timezone): {timestamp}")

    except ValueError:
        raise ValueError(f"Invalid timestamp format: {timestamp}")


def get_cached_metric(metric_name: str):
    """
    Retrieve the last cached value of a metric.
    """
    key = f"metric:{metric_name}"
    data = redis_client.get(key)
    return json.loads(data) if data else None


def set_alert_state(rule_id: str):
    """
    Mark an alert as triggered in Redis to prevent duplicate alerts.
    """
    key = f"alert:{rule_id}"
    redis_client.setex(key, REDIS_ALERT_EXPIRY, "triggered")


def get_alert_state(rule_id: str):
    """
    Check if an alert is already triggered.
    """
    key = f"alert:{rule_id}"
    return redis_client.exists(key) > 0


def set_recovery_state(rule_id: str):
    """
    Mark an alert as recovered in Redis.
    """
    key = f"recovery:{rule_id}"
    redis_client.setex(key, REDIS_ALERT_EXPIRY, "recovered")


def get_recovery_state(rule_id: str):
    """
    Check if a recovery alert has already been sent.
    """
    key = f"recovery:{rule_id}"
    return redis_client.exists(key) > 0
