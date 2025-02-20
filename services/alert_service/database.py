from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import os
from datetime import timezone

from notifiers.email_notifier import EmailNotifier
from notifiers.telegram_notifier import TelegramNotifier

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")


client = MongoClient(MONGODB_URI)
db = client["moniflow"]
alert_rules = db["alert_rules"]
alert_history = db["alert_history"]

def create_alert_rule(metric_name, threshold, duration, comparison, notification_channels, recipients):
    rule = {
        "metric_name": metric_name,
        "threshold": threshold,
        "duration": duration,
        "comparison": comparison,  # ">", "<", "=="
        "notification_channels": notification_channels,  # ["email", "telegram"]
        "recipients": recipients,  # { "email": [...], "telegram": [...] }
        "created_at": datetime.now(timezone.utc),
        "status": "active"
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
    return {
        ">": value > threshold,
        "<": value < threshold,
        "==": value == threshold,
    }.get(comparison, False)

def send_notifications(rule, metric_value):
    message = f"⚠️ Alert Triggered! {rule['metric_name']} = {metric_value} (Threshold: {rule['threshold']})"
    notified_channels = []

    if "email" in rule["notification_channels"]:
        email_notifier = EmailNotifier("smtp.example.com", 587, "alert@example.com", "password")
        email_notifier.send_alert(message, rule["recipients"].get("email", []))
        notified_channels.append("email")

    if "telegram" in rule["notification_channels"]:
        telegram_notifier = TelegramNotifier("TELEGRAM_BOT_TOKEN")
        telegram_notifier.send_alert(message, rule["recipients"].get("telegram", []))
        notified_channels.append("telegram")

    log_alert(rule["_id"], rule["metric_name"], metric_value, notified_channels)