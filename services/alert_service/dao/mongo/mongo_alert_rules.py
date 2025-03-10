import logging
from datetime import datetime, timezone
from bson import ObjectId, errors
from pymongo import MongoClient

logger = logging.getLogger(__name__)


class MongoAlertRule:
    """
    Handles MongoDB operations related to alert rules.
    """

    def __init__(self, mongo_client: MongoClient, mongo_db_name: str):
        """
        Initializes the MongoDB alert rule handler.

        Args:
            mongo_client (MongoClient): A shared MongoDB client instance.
        """
        if not isinstance(mongo_client, MongoClient):
            raise TypeError("mongo_client must be an instance of pymongo.MongoClient")

        self.client = mongo_client
        self.db = self.client[mongo_db_name]
        self.collection = self.db["alert_rules"]

    def get_alert_rule_by_id(self, rule_id: str):
        """Retrieve an alert rule by its ID."""
        try:
            object_id = ObjectId(rule_id)
        except errors.InvalidId:
            return None

        rule = self.collection.find_one({"_id": object_id})
        if rule:
            rule["_id"] = str(rule["_id"])
        return rule

    def get_alert_rules(self):
        """Retrieve all alert rules from the database."""
        return [{**rule, "_id": str(rule["_id"])} for rule in self.collection.find({})]

    def delete_alert_rule(self, rule_id: str):
        """Delete an alert rule by its ID."""
        try:
            object_id = ObjectId(rule_id)
        except errors.InvalidId:
            return None

        result = self.collection.delete_one({"_id": object_id})
        return result

    @staticmethod
    def convert_to_seconds(value: int, unit: str) -> int:
        """Convert time units to seconds."""
        unit_multipliers = {"seconds": 1, "minutes": 60, "hours": 3600}
        return value * unit_multipliers.get(unit, 1)  # Default to seconds if invalid unit

    def create_alert_rule(
        self,
        metric_name,
        tags,
        field_name,
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
        """
        if notification_channels is None:
            notification_channels = ["telegram"]
        if recipients is None:
            recipients = {}

        duration_seconds = self.convert_to_seconds(duration_value, duration_unit)

        recovery_seconds = None
        if use_recovery_alert and recovery_time_value and recovery_time_unit:
            recovery_seconds = self.convert_to_seconds(recovery_time_value, recovery_time_unit)

        rule = {
            "metric_name": metric_name,
            "tags": tags,
            "field_name": field_name,
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

        return self.collection.insert_one(rule).inserted_id
