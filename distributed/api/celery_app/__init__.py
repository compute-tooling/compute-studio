import os
import time
import functools
import traceback

import requests
from celery import Celery
from celery.signals import task_postrun
from celery.result import AsyncResult

import s3like


COMP_URL = os.environ.get("COMP_URL")
COMP_API_USER = os.environ.get("COMP_API_USER")
COMP_API_USER_PASS = os.environ.get("COMP_API_USER_PASS")

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379"
)

OUTPUTS_VERSION = os.environ.get("OUTPUTS_VERSION")

task_routes = {
    # '{project_name}_tasks.*': {'queue': '{project_name}_queue'},
    "hdoupe_matchups_tasks.sim": {"queue": "hdoupe_matchups_queue"},
    "hdoupe_matchups_tasks.inputs_get": {"queue": "hdoupe_matchups_inputs_queue"},
    "hdoupe_matchups_tasks.inputs_parse": {"queue": "hdoupe_matchups_inputs_queue"},
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
        task = args[0]
        task_id = task.request.id
        start = time.time()
        traceback_str = None
        res = {}
        try:
            outputs = func(*args, **kwargs)
            if task.name.endswith("sim"):
                version = outputs.pop("version", OUTPUTS_VERSION)
                if version == "v0":
                    res["result"] = dict(outputs, **{"version": version})
                else:
                    outputs = s3like.write_to_s3like(task_id, outputs)
                    res["result"] = {"outputs": outputs, "version": version}
            else:
                res["result"] = outputs
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
            auth=(COMP_API_USER, COMP_API_USER_PASS),
        )
        print("resp", resp.status_code)
        if resp.status_code == 400:
            print("errors", resp.json())
