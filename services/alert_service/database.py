import os
from bson import ObjectId, errors
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
from datetime import timezone
from notifiers.email_notifier import EmailNotifier
from notifiers.telegram_notifier import TelegramNotifier

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
TEST_DB_NAME = "moniflow_test"

# If tests are running, use the test database
if "pytest" in os.environ.get("_", ""):
    MONGO_URI = f"mongodb://admin:password@mongo:27017/{TEST_DB_NAME}"


client = MongoClient(MONGO_URI)
db = client["moniflow"]
alert_rules = db["alert_rules"]
alert_history = db["alert_history"]


def get_alert_rule_by_id(rule_id: str):
    """Retrieve an alert rule by its ID."""
    try:
        object_id = ObjectId(rule_id)
    except errors.InvalidId:
        return None

    rule = alert_rules.find_one({"_id": object_id})
    if rule:
        rule["_id"] = str(rule["_id"])
    return rule


def get_alert_rules():
    """Retrieve all alert rules from the database."""
    return [{**rule, "_id": str(rule["_id"])} for rule in alert_rules.find({})]


def convert_to_seconds(value: int, unit: str) -> int:
    unit_multipliers = {"seconds": 1, "minutes": 60, "hours": 3600}
    return value * unit_multipliers[unit]


def create_alert_rule(
    metric_name,
    threshold,
    duration_value,
    duration_unit,
    comparison,
    use_recovery_alert,
    recovery_time_value=None,
    recovery_time_unit=None,
    notification_channels=None,
    recipients=None,
):
    """
    Creates an alert rule and inserts it into the alert_rules collection.
    Args:
        metric_name (str): The name of the metric to monitor.
        threshold (float): The threshold value for the alert.
        duration_value (int): The duration value for the alert.
        duration_unit (str): The unit of the duration (e.g., 'seconds', 'minutes', 'hours').
        comparison (str): The comparison operator for the alert (e.g., '>', '<', '==').
        use_recovery_alert (bool): Whether to use a recovery alert.
        recovery_time_value (int, optional): The recovery time value. Defaults to None.
        recovery_time_unit (str, optional): The unit of the recovery time (e.g., 'seconds', 'minutes', 'hours'). Defaults to None.
    Returns:
        ObjectId: The ID of the inserted alert rule document.
    """
    if notification_channels is None:
        notification_channels = ["telegram"]
    if recipients is None:
        recipients = {}

    duration_seconds = convert_to_seconds(duration_value, duration_unit)

    recovery_seconds = None
    if use_recovery_alert and recovery_time_value and recovery_time_unit:
        recovery_seconds = convert_to_seconds(recovery_time_value, recovery_time_unit)

    rule = {
        "metric_name": metric_name,
        "threshold": threshold,
        "duration": duration_seconds,
        "comparison": comparison,
        "notification_channels": notification_channels,
        "recipients": recipients,
        "use_recovery_alert": use_recovery_alert,
        "recovery_time": recovery_seconds,
        "created_at": datetime.now(timezone.utc),
        "status": "active",
    }

    return alert_rules.insert_one(rule).inserted_id


def log_alert(rule_id, metric_name, triggered_value, notified_channels):
    alert_entry = {
        "rule_id": rule_id,
        "metric_name": metric_name,
        "triggered_value": triggered_value,
        "timestamp": datetime.now(timezone.utc),
        "notified_channels": notified_channels,
    }
    alert_history.insert_one(alert_entry)


# rule checking logics
def check_alerts(metric_name, metric_value):
    rules = alert_rules.find({"metric_name": metric_name, "status": "active"})

    for rule in rules:
        if evaluate_condition(rule["comparison"], metric_value, rule["threshold"]):
            send_notifications(rule, metric_value)


def evaluate_condition(comparison, value, threshold):
    """
    Evaluates a condition based on the given comparison operator, value, and threshold.
    Args:
        comparison (str): The comparison operator as a string. Supported operators are ">", "<", and "==".
        value (int or float): The value to be compared.
        threshold (int or float): The threshold value to compare against.
    Returns:
        bool: The result of the comparison. Returns False if the comparison operator is not supported.
    """

    return {
        ">": value > threshold,
        "<": value < threshold,
        "==": value == threshold,
    }.get(comparison, False)


def send_notifications(rule, metric_value):
    message = f"⚠️ Alert Triggered! {rule['metric_name']} = {metric_value} (Threshold: {rule['threshold']})"
    notified_channels = []

    if "email" in rule["notification_channels"]:
        email_notifier = EmailNotifier(
            "smtp.example.com", 587, "alert@example.com", "password"
        )
        email_notifier.send_alert(message, rule["recipients"].get("email", []))
        notified_channels.append("email")

    if "telegram" in rule["notification_channels"]:
        telegram_notifier = TelegramNotifier("TELEGRAM_BOT_TOKEN")
        telegram_notifier.send_alert(message, rule["recipients"].get("telegram", []))
        notified_channels.append("telegram")

    log_alert(rule["_id"], rule["metric_name"], metric_value, notified_channels)
