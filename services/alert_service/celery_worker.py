import os
from celery import Celery

REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "password")
REDIS_URL = f"redis://:{REDIS_PASSWORD}@{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', 6379)}/0"

celery = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)

celery.autodiscover_tasks(["tasks"])
