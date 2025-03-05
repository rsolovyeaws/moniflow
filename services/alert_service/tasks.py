import logging
import json

from pydantic import ValidationError

from celery_worker import celery
from database import alert_rules
from dao.redis.key_schema import KeySchema
from models import AlertRuleSchema
from dao.redis.metrics import RedisMetrics
from redis_config import redis_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

redis_metrics = RedisMetrics(redis_client)

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
        metric_data = redis_metrics.lpop("moniflow:metrics")

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

            # Query Redis for the last `duration_value`
            metric_values = redis_metrics.get_metric_values(
                redis_key, validated_rule.duration_value, validated_rule.duration_unit
            )

            logger.info(f"Fetched {len(metric_values)} values for {redis_key}: {metric_values}")

            valid_keys.append(redis_key)

        except ValidationError as e:
            logger.error(f"Skipping invalid alert rule: {e.errors()}")

    logger.info(f"Processed {len(valid_keys)} valid alert rules and generated Redis keys: {valid_keys}")
