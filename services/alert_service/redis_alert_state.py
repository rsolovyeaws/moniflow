import redis
import logging

logger = logging.getLogger(__name__)


class RedisAlertState:
    """
    Handles storing and retrieving alert and recovery states from Redis.
    """

    def __init__(self, redis_client: redis.Redis):
        """
        Initialize RedisAlertState with a Redis connection.

        Args:
            redis_client (redis.Redis): A Redis connection object.
        """
        if not isinstance(redis_client, redis.Redis):
            raise TypeError("redis_client must be an instance of redis.Redis")
        self.redis_client = redis_client

    def set_alert_state(self, rule_id: str, expiry: int = 300):
        """
        Mark an alert as triggered in Redis.

        Args:
            rule_id (str): The unique identifier for the alert rule.
            expiry (int): Expiry time in seconds (default: 300s).
        """
        key = f"moniflow:alert_state:{rule_id}"
        self.redis_client.setex(key, expiry, "triggered")
        logger.info(f"Set alert state: {key} (expires in {expiry}s)")

    def get_alert_state(self, rule_id: str) -> bool:
        """
        Check if an alert is already triggered.

        Args:
            rule_id (str): The unique identifier for the alert rule.

        Returns:
            bool: True if alert is active, False otherwise.
        """
        key = f"moniflow:alert_state:{rule_id}"
        return self.redis_client.exists(key) > 0

    def set_recovery_state(self, rule_id: str, expiry: int = 300):
        """
        Mark an alert as recovered in Redis.

        Args:
            rule_id (str): The unique identifier for the alert rule.
            expiry (int): Expiry time in seconds (default: 300s).
        """
        key = f"moniflow:recovery_state:{rule_id}"
        self.redis_client.setex(key, expiry, "recovered")
        logger.info(f"Set recovery state: {key} (expires in {expiry}s)")

    def get_recovery_state(self, rule_id: str) -> bool:
        """
        Check if a recovery alert has already been sent.

        Args:
            rule_id (str): The unique identifier for the alert rule.

        Returns:
            bool: True if recovery is active, False otherwise.
        """
        key = f"moniflow:recovery_state:{rule_id}"
        return self.redis_client.exists(key) > 0
