import logging

from base import RedisDaoBase

logger = logging.getLogger(__name__)


class RedisAlertState(RedisDaoBase):
    """
    Handles storing and retrieving alert and recovery states from Redis.
    """

    def set_alert_state(self, rule_id: str, expiry: int = 300):
        """
        Mark an alert as triggered in Redis.

        Args:
            rule_id (str): The unique identifier for the alert rule.
            expiry (int): Expiry time in seconds (default: 300s).
        """
        key = self.key_schema.build_alert_state_key(rule_id)
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
        key = self.key_schema.build_alert_state_key(rule_id)
        return self.redis_client.exists(key) > 0

    def set_recovery_state(self, rule_id: str, expiry: int = 300):
        """
        Mark an alert as recovered in Redis.

        Args:
            rule_id (str): The unique identifier for the alert rule.
            expiry (int): Expiry time in seconds (default: 300s).
        """
        key = self.key_schema.build_recovery_state_key(rule_id)
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
        key = self.key_schema.build_recovery_state_key(rule_id)
        return self.redis_client.exists(key) > 0
