from fastapi import FastAPI, HTTPException
import redis
from database import (
    create_alert_rule,
    delete_alert_rule,
    get_alert_rule_by_id,
    get_alert_rules,
)
from notifiers.telegram_notifier import TelegramNotifier
from redis_handler import store_metric_in_cache
from models import AlertRuleCreate, Metric

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Alert Service Running"}


@app.post("/alerts/")
def create_alert(rule: AlertRuleCreate):
    """
    Creates an alert rule based on the provided AlertRuleCreate object.
    Args:
        rule (AlertRuleCreate): The alert rule creation object containing the necessary parameters.
    Returns:
        dict: A dictionary containing a success message and the ID of the created alert rule.
    """

    rule_dict = rule.model_dump()

    # Ensure recovery time is stored only if enabled
    if not rule.use_recovery_alert:
        rule_dict["recovery_time_value"] = None
        rule_dict["recovery_time_unit"] = None

    rule_id = create_alert_rule(**rule_dict)
    return {"message": "Alert rule created", "rule_id": str(rule_id)}


@app.get("/alerts/{rule_id}")
def get_alert(rule_id: str):
    """
    Retrieve an alert rule by its ID.
    Args:
        rule_id (str): The ID of the alert rule to retrieve.
    Returns:
        dict: The alert rule data if found.
    Raises:
        HTTPException: If the alert rule is not found, raises a 404 HTTP exception.
    """

    rule = get_alert_rule_by_id(rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return rule


@app.get("/alerts/")
def get_alerts():
    """Retrieve all alert rules from the database."""
    return {"alert_rules": get_alert_rules()}


@app.delete("/alerts/{rule_id}")
def delete_alert(rule_id: str):
    """
    Delete an alert rule by its ID.
    Args:
        rule_id (str): The ID of the alert rule to delete.
    Returns:
        dict: A dictionary containing a success message.
    Raises:
        HTTPException: If the alert rule is not found, raises a 404 HTTP exception.
    """

    result = delete_alert_rule(rule_id)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return {"message": "Alert rule deleted"}


@app.post("/metrics/")
async def cache_metric(metric: Metric):
    """
    Cache incoming metric values with a timestamp.
    Key format: "metric:{metric_name}"
    """
    metric_dict = metric.model_dump()

    try:
        store_metric_in_cache(metric_dict)
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="Redis is unavailable. Metric not cached.")

    return {"message": "Metric cached"}


# TEST DEBUG
@app.get("/bot-test/")
async def send_bot_message():
    notifier = TelegramNotifier()
    await notifier.send_alert("Hello, this is a test message")
    return {"message": "Test message sent"}
