from pydantic import BaseModel, Field
from typing import Dict, List, Literal
from datetime import datetime, timezone


class AlertRuleSchema(BaseModel):
    """
    Pydantic model for validating stored alert rules.
    Used internally when fetching from MongoDB.
    """

    metric_name: str = Field(..., min_length=1)
    tags: Dict[str, str] = Field(..., min_length=1)
    field_name: str = Field(..., min_length=1)
    threshold: float
    duration_value: int = Field(..., gt=0)
    duration_unit: Literal["seconds", "minutes", "hours"]
    comparison: Literal[">", "<", "=="]
    notification_channels: List[str]
    recipients: Dict[str, List[str]]
    use_recovery_alert: bool
    recovery_time_value: int | None = Field(None, ge=0)
    recovery_time_unit: Literal["seconds", "minutes", "hours"] | None


class AlertRuleCreate(BaseModel):
    """
    Pydantic model for validating API requests to create a new alert rule.
    Has default values for optional fields.
    """

    metric_name: str  # matches measurment
    tags: Dict[str, str] = Field(..., min_length=1)
    field_name: str  # Matches a field inside `fields`
    threshold: float
    duration_value: int = Field(..., gt=0)  # Must be positive
    duration_unit: Literal["seconds", "minutes", "hours"] = "seconds"  # Default to seconds
    comparison: Literal[">", "<", "=="]
    notification_channels: List[str] = ["telegram"]  # Default to Telegram
    recipients: Dict[str, List[str]] = {}  # Default to empty
    use_recovery_alert: bool = False  # Default disabled
    recovery_time_value: int | None = Field(None, ge=0)  # Only used if recovery alerts are enabled
    recovery_time_unit: Literal["seconds", "minutes", "hours"] | None = None


class Metric(BaseModel):
    measurement: str
    tags: Dict[str, str] = Field(..., min_length=1)
    fields: Dict[str, float] = Field(..., min_length=1)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
