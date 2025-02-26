from datetime import datetime, timezone
from database import get_alert_rules, log_alert
from redis_handler import (
    cache_metric,
    get_cached_metric,
    set_alert_state,
    get_alert_state,
    set_recovery_state,
    get_recovery_state,
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
        recovery_time = rule["recovery_time"]

        # Evaluate threshold condition
        triggered = evaluate_condition(comparison, metric_value, threshold)

        rule_id = str(rule["_id"])

        if triggered:
            if not get_alert_state(rule_id):  # Avoid duplicate alerts
                print(f"Alert Triggered: {metric_name} {comparison} {threshold}")
                log_alert(
                    rule_id, metric_name, metric_value, rule["notification_channels"]
                )
                set_alert_state(rule_id)  # Mark as triggered
        else:
            # Handle recovery alert
            if use_recovery_alert and not get_recovery_state(rule_id):
                print(f"Recovery: {metric_name} is back to normal.")
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
