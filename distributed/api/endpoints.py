import json
import os
import re

from flask import Blueprint, request, make_response
from celery.result import AsyncResult
from celery import chord
import redis

from api.celery_app import celery_app

bp = Blueprint("endpoints", __name__)

queue_name = "celery"
client = redis.Redis.from_url(
    os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
)


def clean(word):
    return re.sub("[^0-9a-zA-Z]+", "", word).lower()


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
    endpoint = async_endpoint
    return route_to_task(owner, app_name, endpoint, action)


@bp.route("/get_job", methods=["GET"])
def results():
    job_id = request.args.get("job_id", "")
    async_result = AsyncResult(job_id)
    if async_result.ready() and async_result.successful():
        return json.dumps(async_result.result)
    elif async_result.failed():
        print("traceback", async_result.traceback)
        return json.dumps(
            {"status": "WORKER_FAILURE", "traceback": async_result.traceback}
        )
    else:
        resp = make_response("not ready", 202)
        return resp


@bp.route("/query_job", methods=["GET"])
def query_results():
    job_id = request.args.get("job_id", "")
    async_result = AsyncResult(job_id)
    print("async_result", async_result.state)
    if async_result.ready() and async_result.successful():
        return "YES"
    elif async_result.failed():
        return "FAIL"
    else:
        return "NO"
