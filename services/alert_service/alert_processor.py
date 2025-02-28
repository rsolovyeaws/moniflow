import os
import redis
import logging
from database import get_alert_rules, log_alert
from redis_handler import (
    set_alert_state,
    get_alert_state,
    set_recovery_state,
    get_recovery_state,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0)),
    decode_responses=True,
)


def evaluate_alerts(metric_name, metric_value):
    """
    Evaluate incoming metrics against alert rules.
    If a rule is triggered, send an alert and update Redis to prevent duplicates.
    If a recovery condition is met, send a recovery alert.
    """
    rules = get_alert_rules()
    for rule in rules:
        if rule["metric_name"] != metric_name or rule["status"] != "active":
            continue

        threshold = rule["threshold"]
        comparison = rule["comparison"]
        use_recovery_alert = rule["use_recovery_alert"]

        triggered = evaluate_condition(comparison, metric_value, threshold)
        rule_id = str(rule["_id"])

        if triggered:
            if not get_alert_state(rule_id):  # Avoid duplicate alerts
                logger.info(f"Alert Triggered: {metric_name} {comparison} {threshold}")
                log_alert(rule_id, metric_name, metric_value, rule["notification_channels"])
                set_alert_state(rule_id)
        else:
            if use_recovery_alert and not get_recovery_state(rule_id):
                logger.info(f"Recovery: {metric_name} is back to normal.")
                set_recovery_state(rule_id)


def evaluate_condition(comparison, value, threshold):
    """
    Evaluates a condition based on the given comparison operator.
    """
    return {
        ">": value > threshold,
        "<": value < threshold,
        "==": value == threshold,
    }.get(comparison, False)
