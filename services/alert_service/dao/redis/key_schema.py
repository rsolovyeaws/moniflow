class KeySchema:
    """
    Handles key formatting for Redis.
    """

    @staticmethod
    def build_redis_metric_key(metric_name: str, tags: dict, field_name: str) -> str:
        """
        Construct a Redis key.

        Redis Key Format:
            moniflow:metrics:{metric_name}:{sorted_tags}:{field_name}

        Args:
            metric_name (str): The metric name.
            tags (dict): Dictionary of tags.
            field_name (str): The specific field name.

        Returns:
            str: The Redis key formatted for Redis storage.
        """
        sorted_tags_str = ",".join(f"{key}={value}" for key, value in sorted(tags.items()))
        return f"moniflow:metrics:{metric_name}:{sorted_tags_str}:{field_name}"

    @staticmethod
    def build_alert_state_key(rule_id: str) -> str:
        """
        Construct a Redis key for tracking active alert state.

        Redis Key Format:
            moniflow:alert_state:{rule_id}

        Args:
            rule_id (str): Unique identifier for the alert rule.

        Returns:
            str: The Redis key for storing alert state.
        """
        return f"moniflow:alert_state:{rule_id}"

    @staticmethod
    def build_recovery_state_key(rule_id: str) -> str:
        """
        Construct a Redis key for tracking recovery alert state.

        Redis Key Format:
            moniflow:recovery_state:{rule_id}

        Args:
            rule_id (str): Unique identifier for the alert rule.

        Returns:
            str: The Redis key for storing recovery state.
        """
        return f"moniflow:recovery_state:{rule_id}"
