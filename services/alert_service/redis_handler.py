import os
import redis
import json

# Load environment variables
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_ALERT_EXPIRY = int(
    os.getenv("REDIS_ALERT_EXPIRY", "300")
)  # 5 minutes default expiry

# Establish Redis connection
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True,
)


def cache_metric(metric_name: str, value: float, timestamp: str):
    """
    Cache incoming metric values with a timestamp.
    Key format: "metric:{metric_name}"
    """
    key = f"metric:{metric_name}"
    data = {"value": value, "timestamp": timestamp}
    redis_client.setex(key, REDIS_ALERT_EXPIRY, json.dumps(data))


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
