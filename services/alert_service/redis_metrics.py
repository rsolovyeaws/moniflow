import time
import redis
import logging

logger = logging.getLogger(__name__)


class RedisMetrics:
    """
    Handles querying stored metrics from Redis.
    """

    def __init__(self, redis_client: redis.Redis):
        """
        Initialize RedisMetrics with a Redis connection.

        Args:
            redis_client (redis.Redis): A Redis connection object.
        """
        if not isinstance(redis_client, redis.Redis):
            raise TypeError("redis_client must be an instance of redis.Redis")
        self.redis_client = redis_client

    def get_metric_values(self, redis_key: str, duration_value: int, duration_unit: str):
        """
        Fetch metric values from Redis using a precomputed key.

        Steps:
        1. Validate inputs.
        2. Calculate the time range based on `duration_value` & `duration_unit`.
        3. Query Redis using the provided key for values in that range.

        Args:
            redis_key (str): The **precomputed Redis key** from Celery task.
            duration_value (int): The duration value for querying historical data.
            duration_unit (str): The duration unit ('seconds', 'minutes', 'hours').

        Returns:
            List[float]: A list of metric values for the given time range.
        """
        # Validate inputs
        if not isinstance(redis_key, str) or not redis_key.strip():
            raise ValueError("Invalid redis_key: must be a non-empty string.")
        if not isinstance(duration_value, int) or duration_value <= 0:
            raise ValueError("Invalid duration_value: must be a positive integer.")
        if duration_unit not in {"seconds", "minutes", "hours"}:
            raise ValueError("Invalid duration_unit: must be 'seconds', 'minutes', or 'hours'.")

        # Calculate the time range
        current_time = int(time.time())
        duration_seconds = self._convert_duration_to_seconds(duration_value, duration_unit)
        min_time = current_time - duration_seconds

        try:
            # Query Redis for values within the time range
            values = self.redis_client.zrangebyscore(redis_key, min_time, current_time)
            return [float(v) for v in values] if values else []

        except redis.RedisError as e:
            logger.error(f"Redis error while fetching {redis_key}: {e}")
            return []

    @staticmethod
    def _convert_duration_to_seconds(value: int, unit: str) -> int:
        """
        Convert duration to seconds.

        Args:
            value (int): The numeric value of duration.
            unit (str): The unit of time ('seconds', 'minutes', 'hours').

        Returns:
            int: The duration in seconds.

        Raises:
            ValueError: If the duration unit is invalid.
        """
        conversion = {"seconds": 1, "minutes": 60, "hours": 3600}
        if unit not in conversion:
            raise ValueError(f"Invalid duration unit: {unit}. Must be 'seconds', 'minutes', or 'hours'.")
        return value * conversion[unit]
