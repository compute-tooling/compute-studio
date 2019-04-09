import os
import time
import functools
from collections import defaultdict

from celery import Celery
from celery.signals import task_postrun
from celery.result import AsyncResult

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379"
)

task_routes = {
    # '{project_name}_tasks.*': {'queue': '{project_name}_queue'},
    "hdoupe_matchups_tasks.sim": {"queue": "hdoupe_matchups_queue"},
    "hdoupe_matchups_tasks.inputs_*": {"queue": "hdoupe_matchups_inputs_queue"},
    "pslmodels_taxbrain_tasks.sim": {"queue": "pslmodels_taxbrain_queue"},
    "pslmodels_taxbrain_tasks.inputs_*": {"queue": "pslmodels_taxbrain_inputs_queue"},
    "error_app_tasks.sim": {"queue": "error_app_queue"},
    "error_app_tasks.inputs_*": {"queue": "error_app_inputs_queue"},
}


celery_app = Celery(
    "celery_app", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND
)
celery_app.conf.update(
    task_serializer="json", accept_content=["msgpack", "json"], task_routes=task_routes
)


def task_wrapper(func):
    @functools.wraps(func)
    def f(*args, **kwargs):
        start = time.time()
        traceback = None
        res = defaultdict(dict)
        try:
            res["result"] = func(*args, **kwargs)
        except Exception as e:
            traceback = str(e)
        finish = time.time()
        if "meta" not in res:
            res["meta"] = {}
        res["meta"]["task_times"] = [finish - start]
        if traceback is None:
            res["status"] = "SUCCESS"
        else:
            res["status"] = "FAIL"
            res["traceback"] = traceback
        return res

    return f
