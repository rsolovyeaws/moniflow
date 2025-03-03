import logging
import redis
import json
import os

from celery_worker import celery
from database import alert_rules
from redis_key_schema import KeySchema
from pydantic import ValidationError
from models import AlertRuleSchema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0)),
    password=os.getenv("REDIS_PASSWORD", None),
    decode_responses=True,
)

celery.conf.beat_schedule = {
    "process_metrics_every_thirty_seconds": {
        "task": "alert_service.process_metrics",
        "schedule": 30.0,  # seconds
    },
    "fetch_alert_rules_every_sixty_seconds": {
        "task": "alert_service.fetch_alert_rules",
        "schedule": 60.0,  # seconds
    },
}


@celery.task(name="alert_service.process_metrics")
def process_metrics():
    """
    Celery task that pulls metrics from Redis and processes them.
    """
    while True:
        metric_data = redis_client.lpop("moniflow:metrics")

        if metric_data is None:
            break

        metric = json.loads(metric_data)
        logger.info(f"Processing metric: {metric}")


@celery.task(name="alert_service.fetch_alert_rules")
def fetch_alert_rules():
    """
    Celery task that fetches alert rules from the database, validates them,
    and generates Redis keys for processing.
    """
    alert_rules_data = list(alert_rules.find({}))

    valid_keys = []
    for rule in alert_rules_data:
        try:
            # Validate alert rule using Pydantic
            validated_rule = AlertRuleSchema(**rule)

            # Generate Redis key using validated rule
            redis_key = KeySchema.build_redis_metric_key(
                validated_rule.metric_name, validated_rule.tags, validated_rule.field_name
            )
            valid_keys.append(redis_key)

        except ValidationError as e:
            logger.error(f"Skipping invalid alert rule: {e.errors()}")

    logger.info(f"Processed {len(valid_keys)} valid alert rules and generated Redis keys: {valid_keys}")
