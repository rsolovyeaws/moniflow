from celery import shared_task
import logging
import redis
import json
import os
from database import get_alert_rules, log_alert
from redis_handler import set_alert_state, get_alert_state, set_recovery_state, get_recovery_state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0)),
    password=os.getenv("REDIS_PASSWORD", None),
    decode_responses=True,
)


@shared_task(name="alert_service.process_metrics")
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
