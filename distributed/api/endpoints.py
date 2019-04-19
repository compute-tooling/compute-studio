from flask import Blueprint, request, make_response
from celery.result import AsyncResult
from celery import chord

import redis
import json
import msgpack
import os

from api.celery_app import hdoupe_matchups_tasks, pslmodels_taxbrain_tasks

task_modules = {
    ("hdoupe", "Matchups"): hdoupe_matchups_tasks,
    ("PSLmodels", "Tax-Brain"): pslmodels_taxbrain_tasks,
    # ("error", "app"): error_app_tasks
}

if os.environ.get("DEVELOP", ""):
    from api.celery_app import error_app_tasks

    task_modules[("error", "app")] = error_app_tasks

bp = Blueprint("endpoints", __name__)

queue_name = "celery"
client = redis.Redis.from_url(
    os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
)


def sim_endpoint(compute_task):
    print("sim endpoint")
    data = request.get_data()
    inputs = msgpack.loads(data, encoding="utf8", use_list=True)
    print("inputs", inputs)
    result = compute_task.apply_async(kwargs=inputs, serializer="msgpack")
    length = client.llen(queue_name) + 1
    data = {"job_id": str(result), "qlength": length}
    return json.dumps(data)


def sync_endpoint(compute_task):
    print("io endpoint")
    data = request.get_data()
    inputs = msgpack.loads(data, encoding="utf8", use_list=True)
    print("inputs", inputs)
    result = compute_task.apply_async(kwargs=inputs, serializer="msgpack")
    # try:
    print("getting...")
    result = result.get()
    # except Exception as e:

    # length = client.llen(queue_name) + 1
    # data = {'job_id': str(result), 'qlength': length}
    return json.dumps(result)


def route_to_task(owner, app_name, endpoint, action):
    print("getting...", owner, app_name, endpoint, action)
    module = task_modules.get((owner, app_name), None)
    print("got module", module)
    if module is not None:
        return endpoint(getattr(module, action))
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
    endpoint = sync_endpoint
    return route_to_task(owner, app_name, endpoint, action)


@bp.route("/<owner>/<app_name>/sim", methods=["POST"])
def endpoint_sim(owner, app_name):
    action = "sim"
    endpoint = sim_endpoint
    return route_to_task(owner, app_name, endpoint, action)


@bp.route("/get_job", methods=["GET"])
def results():
    job_id = request.args.get("job_id", "")
    async_result = AsyncResult(job_id)
    if async_result.ready() and async_result.successful():
        return json.dumps(async_result.result)
    elif async_result.failed():
        print("traceback", async_result.traceback)
        return {"status": "WORKER_FAILURE", "traceback": async_result.traceback}
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
