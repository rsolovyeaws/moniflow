import os
import redis
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# REDIS_HOST = os.getenv("REDIS_HOST", "redis")
# REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
# REDIS_DB = int(os.getenv("REDIS_DB", "0"))
# REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_ALERT_EXPIRY = int(os.getenv("REDIS_ALERT_EXPIRY", "300"))

if os.getenv("TEST_REDIS_HOST"):
    REDIS_HOST = os.getenv("TEST_REDIS_HOST", "moniflow-test-redis")
    REDIS_PORT = int(os.getenv("TEST_REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("TEST_REDIS_DB", 1))
    REDIS_PASSWORD = os.getenv("TEST_REDIS_PASSWORD", None)  # Use test password
else:
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)  # Use production password

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True,
)


def store_metric_in_cache(metric_data: dict):
    """
    Store incoming metric in Redis for processing.

    Redis List: "moniflow:metrics"
    This will store metrics as a queue for Celery workers to process.

    Args:
        metric_data (dict): The metric data to store.
    """
    try:
        redis_client.rpush("moniflow:metrics", json.dumps(metric_data))
    except redis.RedisError as e:
        logger.error(f"Redis Error: {e}")
        raise


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
