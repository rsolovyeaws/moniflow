import logging
import json

from pydantic import ValidationError

from celery_worker import celery
from database import alert_rules
from models import AlertRuleSchema
from dao.redis.metrics import RedisMetrics
from redis_config import redis_client
from evaluators.alert_evaluator import AlertEvaluator

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
    Celery task that fetches alert rules from the database, validates them, and fetches metric values...
    WIP:
    """
    alert_rules_data = list(alert_rules.find({}))

    valid_rules = []
    for rule in alert_rules_data:
        try:
            # Validate alert rule using Pydantic
            validated_rule = AlertRuleSchema(**rule)

            metric_values = redis_metrics.get_metric_values(
                validated_rule.metric_name,
                validated_rule.tags,
                validated_rule.field_name,
                validated_rule.duration_value,
                validated_rule.duration_unit,
            )

            logger.info(f"Fetched {len(metric_values)} values for {validated_rule}.")

            valid_rules.append(validated_rule)

            if AlertEvaluator.from_alert_rule(validated_rule, metric_values):
                logger.warning(f"Alert triggered for {validated_rule.metric_name}!")
                # TODO: Send notification (next step)

        except ValidationError as e:
            logger.error(f"Skipping invalid alert rule: {e.errors()}")

    logger.info(f"Processed {len(valid_rules)} valid alert rules out of {len(alert_rules_data)}.")
