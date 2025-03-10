import logging
from datetime import datetime
from pymongo import MongoClient, errors

logger = logging.getLogger(__name__)


class MongoAlertHistory:
    """
    Handles storing alert history in MongoDB for long-term tracking.
    """

    def __init__(self, mongo_client: MongoClient, mongo_db_name: str):
        """
        Initializes the MongoDB alert history handler.

        Args:
            mongo_client (MongoClient): A shared MongoDB client instance.
        """
        if not isinstance(mongo_client, MongoClient):
            raise TypeError("mongo_client must be an instance of pymongo.MongoClient")

        self.client = mongo_client
        self.db = self.client[mongo_db_name]
        self.collection = self.db["alert_history"]

    @classmethod
    def setup_indexes(cls, mongo_client: MongoClient, mongo_db_name: str):
        """
        Ensures the `timestamp` index exists to improve query performance and auto-delete old alerts.
        This function should only be called once at application startup.
        """
        db = mongo_client[mongo_db_name]
        collection = db["alert_history"]

        # Ensure a TTL index on `timestamp` for automatic deletion after 30 days
        try:
            collection.create_index("timestamp", expireAfterSeconds=60 * 60 * 24 * 30)
            logger.info("Ensured `timestamp` index exists for alert history.")
        except errors.PyMongoError as e:
            logger.error(f"Failed to create index on `timestamp`: {e}")

    def log_alert(self, rule_id: str, metric_name: str, tags: dict, field_name: str, status: str):
        """
        Logs an alert event (triggered/recovered) into MongoDB.

        Args:
            rule_id (str): Unique identifier for the alert rule.
            metric_name (str): The metric name.
            tags (dict): The tags for the metric.
            field_name (str): The specific field name.
            status (str): "triggered" or "recovered".
        """
        log_entry = {
            "rule_id": rule_id,
            "metric_name": metric_name,
            "tags": tags,
            "field_name": field_name,
            "status": status,
            "timestamp": datetime.utcnow(),
        }

        try:
            self.collection.insert_one(log_entry)
            logger.info(f"Logged alert event in MongoDB: {log_entry}")
        except errors.PyMongoError as e:
            logger.error(f"Failed to log alert event in MongoDB: {e}")
