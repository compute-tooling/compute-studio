import functools
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
from cs_dask_sim import dask_sim, done_callback


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
        config[model_id] = {
            "cluster_type": model["cluster_type"],
            "time_out": model["exp_task_time"] * 1.25,
        }
    print("made config: ", config)
    return config


CONFIG = get_cs_config()


def get_cluster_type(owner, app_name):
    model_id = clean(owner), clean(app_name)
    # allowed to return None
    return CONFIG.get(model_id, {}).get("cluster_type")


def get_time_out(owner, app_name):
    model_id = clean(owner), clean(app_name)
    return CONFIG[model_id]["time_out"]


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
    print("got data", data)
    if not data:
        inputs = {}
    else:
        inputs = json.loads(data)
    print("inputs", inputs)
    result = celery_app.signature(compute_task, kwargs=inputs).delay()
    print("getting...")
    result = result.get()
    return json.dumps(result)


def dask_endpoint(owner, app_name, action):
    """
    Route dask simulation to appropriate dask scheduluer.
    """
    print(f"dask endpoint: {owner}/{app_name}/{action}")
    data = request.get_data()
    inputs = json.loads(data)
    print("inputs", inputs)
    addr = dask_scheduler_address(owner, app_name)
    job_id = str(uuid.uuid4())

    # Worker needs the job_id to push the results back to the
    # webapp.
    # The url and api token are passed as args insted of env
    # variables so that the wrapper has access to them
    # but the model does not.
    inputs.update(
        {
            "job_id": job_id,
            "comp_url": os.environ.get("COMP_URL"),
            "comp_api_token": os.environ.get("COMP_API_TOKEN"),
            "timeout": get_time_out(owner, app_name),
        }
    )

    with Client(addr) as c:
        fut = c.submit(dask_sim, **inputs)
        fire_and_forget(fut)
        return {"job_id": job_id, "qlength": 1}


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


@bp.route("/<owner>/<app_name>/version", methods=["POST"])
def endpoint_version(owner, app_name):
    action = "inputs_version"
    endpoint = sync_endpoint
    return route_to_task(owner, app_name, endpoint, action)


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
    print("owner, app_name", owner, app_name)
    cluster_type = get_cluster_type(owner, app_name)
    print(f"cluster type is {cluster_type}")
    if cluster_type == "single-core":
        return route_to_task(owner, app_name, async_endpoint, action)
    elif cluster_type == "dask":
        return dask_endpoint(owner, app_name, action)
    else:
        return json.dumps({"error": "model does not exist."}), 404


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


@bp.route("/reset-config/", methods=["GET"])
def reset_config():
    CONFIG.update(get_cs_config())
    return json.dumps({"status": "SUCCESS"}), 200
