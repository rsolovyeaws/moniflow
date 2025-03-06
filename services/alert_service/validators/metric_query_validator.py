class MetricQueryValidator:
    """Validates input parameters before querying Redis for metric values."""

    @staticmethod
    def validate(metric_name: str, tags: dict, field_name: str, duration_value: int, duration_unit: str):
        """Validates parameters for fetching metric values."""
        for param, param_name in [(metric_name, "metric_name"), (field_name, "field_name")]:
            if not isinstance(param, str) or not param.strip():
                raise ValueError(f"Invalid {param_name}: must be a non-empty string.")

        if not isinstance(tags, dict) or not tags:
            raise ValueError("Invalid tags: must be a non-empty dictionary.")

        if not isinstance(duration_value, int) or duration_value <= 0:
            raise ValueError("Invalid duration_value: must be a positive integer.")

        if duration_unit not in {"seconds", "minutes", "hours"}:
            raise ValueError("Invalid duration_unit: must be one of 'seconds', 'minutes', or 'hours'.")
