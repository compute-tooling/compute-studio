import os
import time
from collections import defaultdict

from celery import Celery

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379"
)

task_routes = {
    # '{project_name}_tasks.*': {'queue': '{project_name}_queue'},
    "hdoupe_matchups_tasks.sim": {"queue": "hdoupe_matchups_queue"},
    "hdoupe_matchups_tasks.inputs_*": {"queue": "hdoupe_matchups_inputs_queue"},
}


celery_app = Celery(
    "celery_app", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND
)
celery_app.conf.update(
    task_serializer="json", accept_content=["msgpack", "json"], task_routes=task_routes
)
