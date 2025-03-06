import time
import redis
import logging

from datetime import datetime, timezone
from dateutil import parser

from dao.redis.base import RedisDaoBase
from validators.metric_query_validator import MetricQueryValidator

logger = logging.getLogger(__name__)


class RedisMetrics(RedisDaoBase):
    """
    Handles querying stored metrics from Redis.
    """

    @staticmethod
    def parse_timestamp(timestamp):
        """
        Convert a strict ISO 8601 timestamp into a UNIX timestamp (seconds).

        Strict Validation:
        - Requires **explicit timezone information** (e.g., 'Z' or '+02:00').
        - **Rejects** timestamps without a timezone.
        - **Supports** standard ISO 8601 formats, including microseconds.

        Args:
            timestamp (str | int): The input timestamp (ISO 8601 string or Unix timestamp).

        Returns:
            int: The converted Unix timestamp.

        Raises:
            ValueError: If the timestamp format is invalid or missing a timezone.

        Examples:
        ---------
        Valid Inputs ✅:
        - "2025-02-26T12:00:00Z"       → ✅ Allowed (UTC)
        - "2025-02-26T14:00:00+02:00"  → ✅ Allowed (UTC conversion)
        - "2025-02-26T10:00:00-02:00"  → ✅ Allowed (UTC conversion)
        - "2025-02-26T12:00:00.123456Z" → ✅ Allowed (Microseconds supported)

        Invalid Inputs ❌:
        - "2025-02-26T12:00:00"   → ❌ REJECTED (Missing timezone)
        - "2025-02-26"            → ❌ REJECTED (Date only, no time)
        - "not-a-timestamp"       → ❌ REJECTED (Invalid format)
        - 1234567890              → ❌ REJECTED (Must be a string)
        """
        if isinstance(timestamp, bool):  # Prevent booleans (Python treats True/False as 1/0)
            raise ValueError("Invalid timestamp format: input must be a string.")

        if isinstance(timestamp, int):  # Unix timestamp is NOT allowed
            raise ValueError("Invalid timestamp format: Unix timestamps are not accepted directly.")

        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError("Invalid timestamp format: must be a non-empty string.")

        try:
            dt = parser.isoparse(timestamp)

            # If no timezone info is provided, reject it
            if dt.tzinfo is None:
                raise ValueError(f"Invalid timestamp format (missing timezone): {timestamp}")

            return int(dt.timestamp())

        except (ValueError, TypeError):
            raise ValueError(f"Invalid timestamp format: {timestamp}")

    def store_metric_in_cache(self, metric_data: dict):
        """
        Store incoming metric in Redis with separate keys per field.

        Redis Sorted Set (ZADD) Format:
            moniflow:metrics:{measurement}:{sorted_tags}:{field_name}

        Example:
            moniflow:metrics:cpu_usage:group=alpha:host=server-1:usage
            moniflow:metrics:cpu_usage:group=alpha:host=server-1:temperature

        Args:
            metric_data (dict): The metric data to store.
        """
        try:
            measurement = metric_data.get("measurement")
            tags = metric_data.get("tags", {})
            fields = metric_data.get("fields", {})
            timestamp = metric_data.get("timestamp", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))

            # Convert timestamp to Unix time
            timestamp = RedisMetrics.parse_timestamp(timestamp)

            # Generate Redis key
            sorted_tags = ":".join(f"{k}={v}" for k, v in sorted(tags.items()))
            for field_name, field_value in fields.items():
                redis_key = f"moniflow:metrics:{measurement}:{sorted_tags}:{field_name}"
                self.redis_client.zadd(redis_key, {field_value: timestamp})

                logger.info(f"Stored in Redis: {redis_key} -> {field_value} at {timestamp}")

        except redis.RedisError as e:
            logger.error(f"Redis Error: {e}")
            raise

    def get_metric_values(self, metric_name: str, tags: dict, field_name: str, duration_value: int, duration_unit: str):
        """
        Fetch metric values from Redis based on metric details.

        Args:
            metric_name (str): Name of the metric.
            tags (dict): Tags associated with the metric.
            field_name (str): Specific field within the metric.
            duration_value (int): Duration to look back.
            duration_unit (str): Unit of duration (seconds, minutes, hours).

        Returns:
            List[float]: A list of metric values within the specified time range.
        """
        MetricQueryValidator.validate(metric_name, tags, field_name, duration_value, duration_unit)

        redis_key = self.key_schema.build_redis_metric_key(metric_name, tags, field_name)

        # Calculate the time range
        current_time = int(time.time())
        duration_seconds = self._convert_duration_to_seconds(duration_value, duration_unit)
        min_time = current_time - duration_seconds

        try:
            # Query Redis
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
