import json
import os
import re
import time
import traceback
import uuid
from collections import defaultdict

from flask import Blueprint, request, make_response
from celery.result import AsyncResult
from celery import chord
from distributed import Client, Future, fire_and_forget
import redis
import requests

from api.celery_app import celery_app


COMP_URL = os.environ.get("COMP_URL")
COMP_API_TOKEN = os.environ.get("COMP_API_TOKEN")

bp = Blueprint("endpoints", __name__)

queue_name = "celery"
client = redis.Redis.from_url(
    os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
)


def clean(word):
    return re.sub("[^0-9a-zA-Z]+", "", word).lower()


def get_cs_config():
    print(f"getting config from: {COMP_URL}/publish/api/")
    resp = requests.get(f"{COMP_URL}/publish/api/")
    if resp.status_code != 200:
        raise Exception(f"Response status code: {resp.status_code}")
    data = resp.json()
    print("got config: ", data)
    config = {}

    for model in data:
        model_id = clean(model["owner"]), clean(model["title"])
        config[model_id] = model["cluster_type"]
    print("made config: ", config)
    return config


CONFIG = get_cs_config()


def get_cluster_type(owner, app_name):
    model_id = clean(owner), clean(app_name)
    return CONFIG.get(model_id, None)


def dask_scheduler_address(owner, app_name):
    owner, app_name = clean(owner), clean(app_name)
    return f"{owner}-{app_name}-dask-scheduler:8786"


def async_endpoint(compute_task):
    print(f"async endpoint {compute_task}")
    data = request.get_data()
    inputs = json.loads(data)
    print("inputs", inputs)
    result = celery_app.signature(compute_task, kwargs=inputs).delay()
    length = client.llen(queue_name) + 1
    data = {"job_id": str(result), "qlength": length}
    return json.dumps(data)


def sync_endpoint(compute_task):
    print(f"io endpoint {compute_task}")
    data = request.get_data()
    inputs = json.loads(data)
    print("inputs", inputs)
    result = celery_app.signature(compute_task, kwargs=inputs).delay()
    print("getting...")
    result = result.get()
    return json.dumps(result)


def done_callback(future):
    print(f"task_id: {future.key}")
    print(f"from dask")
    print(f"state: {future.status}")
    res = future.result()
    res["job_id"] = future.key
    if res["task"].name.endswith("sim"):
        print(f"posting data to {COMP_URL}/outputs/api/")
        resp = requests.put(
            f"{COMP_URL}/outputs/api/",
            json=res["retval"],
            headers={"Authorization": f"Token {COMP_API_TOKEN}"},
        )
        print("resp", resp.status_code)
        if resp.status_code == 400:
            print("errors", resp.json())


def dask_sim(meta_param_dict, adjustment):
    from cs_config import functions

    start = time.time()
    traceback_str = None
    res = {}
    with Client() as c:
        print("c", c)
        # TODO: add and handle timeout
        fut = c.submit(functions.run_model, meta_param_dict, adjustment)
        print("waiting on result", fut)
        try:
            output = fut.result()
            res = {"output": output, "version": "v1"}
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


def dask_endpoint(owner, app_name, action):
    data = request.get_data()
    inputs = json.loads(data)
    addr = dask_scheduler_address(owner, app_name)
    with Client(addr) as c:
        fut = c.submit(dask_sim, key=uuid.uuid4(), **inputs)
        fut.add_done_callback(done_callback)
        fire_and_forget(fut)
        return {"job_id": fut.key, "qlength": 1}


def route_to_task(owner, app_name, endpoint, action):
    owner, app_name = clean(owner), clean(app_name)
    print("getting...", owner, app_name, endpoint, action)
    task_name = f"{owner}_{app_name}_tasks.{action}"
    print("got task_name", task_name)
    print("map", celery_app.amqp.routes)
    if task_name in celery_app.amqp.routes[0].map:
        return endpoint(task_name)
    else:
        return json.dumps({"error": "invalid endpoint"}), 404


@bp.route("/<owner>/<app_name>/inputs", methods=["POST"])
def endpoint_inputs(owner, app_name):
    action = "inputs_get"
    endpoint = sync_endpoint
    return route_to_task(owner, app_name, endpoint, action)


@bp.route("/<owner>/<app_name>/parse", methods=["POST"])
def endpoint_parse(owner, app_name):
    action = "inputs_parse"
    endpoint = async_endpoint
    return route_to_task(owner, app_name, endpoint, action)


@bp.route("/<owner>/<app_name>/sim", methods=["POST"])
def endpoint_sim(owner, app_name):
    action = "sim"
    cluster_type = get_cluster_type(owner, app_name)
    if cluster_type == "single-core":
        endpoint = async_endpoint
    elif cluster_type == "dask":
        endpoint = dask_endpoint
    else:
        return json.dumps({"error": "model does not exist."}), 404

    return route_to_task(owner, app_name, endpoint, action)


@bp.route("/<owner>/<app_name>/get/<job_id>/", methods=["GET"])
def results(owner, app_name, job_id):
    cluster_type = get_cluster_type(owner, app_name)
    if cluster_type == "single-core":
        async_result = AsyncResult(job_id)
        if async_result.ready() and async_result.successful():
            return json.dumps(async_result.result)
        elif async_result.failed():
            print("traceback", async_result.traceback)
            return json.dumps(
                {"status": "WORKER_FAILURE", "traceback": async_result.traceback}
            )
        else:
            return make_response("not ready", 202)
    elif cluster_type == "dask":
        addr = dask_scheduler_address(owner, app_name)
        with Client(addr) as client:
            fut = Future(job_id, client=client)
            if fut.done() and fut.status != "error":
                return fut.result()
            elif fut.done() and fut.status in ("error", "cancelled"):
                return json.dumps(
                    {"status": "WORKER_FAILURE", "traceback": fut.traceback()}
                )
            else:
                return make_response("not ready", 202)
    else:
        return json.dumps({"error": "model does not exist."}), 404


@bp.route("/<owner>/<app_name>/query/<job_id>/", methods=["GET"])
def query_results(owner, app_name, job_id):

    cluster_type = get_cluster_type(owner, app_name)
    if cluster_type == "single-core":
        async_result = AsyncResult(job_id)
        print("celery result", async_result.state)
        if async_result.ready() and async_result.successful():
            return "YES"
        elif async_result.failed():
            return "FAIL"
        else:
            return "NO"
    elif cluster_type == "dask":
        addr = dask_scheduler_address(owner, app_name)
        with Client(addr) as client:
            fut = Future(job_id, client=client)
            print("dask result", fut.status)
            if fut.done() and fut.status != "error":
                return "YES"
            elif fut.done() and fut.status in ("error", "cancelled"):
                return "FAIL"
            else:
                return "NO"
    else:
        return json.dumps({"error": "model does not exist."}), 404
