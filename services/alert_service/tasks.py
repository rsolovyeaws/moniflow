import logging
import json

from pydantic import ValidationError

from celery_worker import celery
from models import AlertRuleSchema
from dao.redis.metrics import RedisMetrics
from dao.redis.alert_state import RedisAlertState
from redis_config import redis_client
from evaluators.alert_evaluator import AlertEvaluator
from dao.mongo.mongo_alert_history import MongoAlertHistory
from dao.mongo.mongo_alert_rules import MongoAlertRule
from mongo_config import mongo_client, MONGO_DB_NAME

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

redis_metrics = RedisMetrics(redis_client)
redis_alert_state = RedisAlertState(redis_client)

# Ensure indexes exist before processing alerts
MongoAlertHistory.setup_indexes(mongo_client, MONGO_DB_NAME)

mongo_alert_history = MongoAlertHistory(mongo_client, MONGO_DB_NAME)
mongo_alert_rules = MongoAlertRule(mongo_client, MONGO_DB_NAME)

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
        metric_data = None  # redis_client.lpop("moniflow:metrics")

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
    alert_rules_data = list(mongo_alert_rules.get_alert_rules())

    valid_rules = []
    for rule in alert_rules_data:
        try:
            # Validate alert rule using Pydantic
            validated_rule = AlertRuleSchema(**rule)

            metric_values = redis_metrics.get_metric_values(
                validated_rule.metric_name, validated_rule.tags, validated_rule.field_name, validated_rule.duration
            )

            logger.info(f"Fetched {len(metric_values)} values for {validated_rule}.")

            valid_rules.append(validated_rule)

            rule_id = str(validated_rule.rule_id)

            if AlertEvaluator.from_alert_rule(validated_rule, metric_values):
                if not redis_alert_state.get_alert_state(rule_id):
                    redis_alert_state.set_alert_state(rule_id, validated_rule.duration)
                    mongo_alert_history.log_alert(rule_id, validated_rule.metric_name, validated_rule.tags, validated_rule.field_name, "triggered")
                    logger.warning(f"Alert triggered for {validated_rule.metric_name}!")
                    # TODO: Send notification (next step)
                else:
                    logger.info(f"Alert already active for {validated_rule.metric_name}, skipping duplicate notification.")
            else:
                if redis_alert_state.get_alert_state(rule_id):
                    redis_alert_state.set_recovery_state(rule_id, validated_rule.recovery_time)
                    mongo_alert_history.log_alert(rule_id, validated_rule.metric_name, validated_rule.tags, validated_rule.field_name, "recovered")
                    logger.info(f"Recovery alert sent for {validated_rule.metric_name}.")
                    # TODO: Send recovery notification

        except ValidationError as e:
            logger.error(f"Skipping invalid alert rule: {e.errors()}")

    logger.info(f"Processed {len(valid_rules)} valid alert rules out of {len(alert_rules_data)}.")
