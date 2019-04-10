import os
import time
import functools
import traceback
from collections import defaultdict

import requests

from celery import Celery
from celery.signals import task_postrun
from celery.result import AsyncResult

COMP_URL = os.environ.get("COMP_URL")

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
        traceback_str = None
        res = defaultdict(dict)
        try:
            res["result"] = func(*args, **kwargs)
        except Exception as e:
            traceback_str = traceback.format_exc()
        finish = time.time()
        if "meta" not in res:
            res["meta"] = {}
        res["meta"]["task_times"] = [finish - start]
        if traceback_str is None:
            res["status"] = "SUCCESS"
        else:
            res["status"] = "FAIL"
            res["traceback"] = traceback_str
        return res

    return f


@task_postrun.connect
def post_results(sender=None, headers=None, body=None, **kwargs):
    print(f'task_id: {kwargs["task_id"]}')
    print(f'task: {kwargs["task"]} {kwargs["task"].name}')
    print(f'is sim: {kwargs["task"].name.endswith("sim")}')
    print(f'state: {kwargs["state"]}')
    kwargs["retval"]["job_id"] = kwargs["task_id"]
    if kwargs["task"].name.endswith("sim"):
        print(f"posting data to {COMP_URL}/outputs/api/")
        resp = requests.put(
            f"{COMP_URL}/outputs/api/",
            json=kwargs["retval"],
            auth=("comp-api", "heyhey2222"),
        )
        print("resp", resp.status_code)
        if resp.status_code == 400:
            print("errors", resp.json())
