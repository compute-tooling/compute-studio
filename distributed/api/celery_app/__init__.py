import os
import time
import functools
import re
import traceback

import requests
from celery import Celery
from celery.signals import task_postrun
from celery.result import AsyncResult

import cs_storage


try:
    from cs_config import functions
except ImportError as ie:
    if os.environ.get("IS_FLASK", "False") == "True":
        functions = None
    else:
        raise ie


COMP_URL = os.environ.get("COMP_URL")
COMP_API_TOKEN = os.environ.get("COMP_API_TOKEN")

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379"
)

OUTPUTS_VERSION = os.environ.get("OUTPUTS_VERSION")


def get_task_routes():
    def clean(name):
        return re.sub("[^0-9a-zA-Z]+", "", name).lower()

    print(f"getting config from: {COMP_URL}/publish/api/")
    resp = requests.get(f"{COMP_URL}/publish/api/")
    if resp.status_code != 200:
        raise Exception(f"Response status code: {resp.status_code}")
    data = resp.json()
    task_routes = {}
    for project in data:
        owner = clean(project["owner"])
        title = clean(project["title"])
        model = f"{owner}_{title}"

        # all apps use celery workers for handling their inputs.
        routes = {
            f"{model}_tasks.inputs_get": {"queue": f"{model}_inputs_queue"},
            f"{model}_tasks.inputs_parse": {"queue": f"{model}_inputs_queue"},
        }

        # only add sim routes for models that use celery workers.
        if project["cluster_type"] == "single-core":
            routes[f"{model}_tasks.sim"] = {"queue": f"{model}_queue"}

        task_routes.update(routes)
    return task_routes


task_routes = get_task_routes()


celery_app = Celery(
    "celery_app", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["msgpack", "json"],
    task_routes=task_routes,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
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
                    res["model_version"] = "NA"
                    res.update(dict(outputs, **{"version": version}))
                else:
                    res["model_version"] = functions.get_version()
                    outputs = cs_storage.write(task_id, outputs)
                    res.update({"outputs": outputs, "version": version})
            else:
                res.update(outputs)
        except Exception:
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
            headers={"Authorization": f"Token {COMP_API_TOKEN}"},
        )
        print("resp", resp.status_code)
        if resp.status_code == 400:
            print("errors", resp.json())
    if kwargs["task"].name.endswith("parse"):
        print(f"posting data to {COMP_URL}/inputs/api/")
        resp = requests.put(
            f"{COMP_URL}/inputs/api/",
            json=kwargs["retval"],
            headers={"Authorization": f"Token {COMP_API_TOKEN}"},
        )
        print("resp", resp.status_code)
        if resp.status_code == 400:
            print("errors", resp.json())
