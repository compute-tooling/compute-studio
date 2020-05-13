import argparse
import functools
import json
import os

import redis
import requests

import cs_storage
from cs_publish.executors.task_wrapper import async_task_wrapper
from cs_publish.executors.celery import get_app


def sim_handler(task_id, meta_param_dict, adjustment):
    from cs_config import functions

    outputs = functions.run_model(meta_param_dict, adjustment)
    print("got result")
    outputs = cs_storage.serialize_to_json(outputs)
    resp = requests.post(
        "http://outputs-processor/write/", json={"task_id": task_id, "outputs": outputs}
    )
    assert resp.status_code == 200, f"Got code: {resp.status_code}"
    return resp.json()


routes = {"sim": sim_handler}


def executor(routes):
    parser = argparse.ArgumentParser(description="CLI for C/S jobs.")
    parser.add_argument("--job-id", "-t", required=True)
    parser.add_argument("--route-name", "-r", required=True)
    args = parser.parse_args()

    async_task_wrapper(args.job_id, routes[args.route_name])


def main():
    executor({"sim": sim_handler})
