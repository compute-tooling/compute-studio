import argparse
import functools
import json
import os

import redis
import requests

import cs_storage
from cs_workers.executors.task_wrapper import async_task_wrapper


def sim_handler(task_id, meta_param_dict, adjustment):
    from cs_config import functions

    outputs = functions.run_model(meta_param_dict, adjustment)
    print("got result")
    outputs = cs_storage.serialize_to_json(outputs)
    print("storing results")
    resp = requests.post(
        "http://outputs-processor/write/", json={"task_id": task_id, "outputs": outputs}
    )
    print("got resp", resp.status_code, resp.url)
    assert resp.status_code == 200, f"Got code: {resp.status_code}"
    return resp.json()


routes = {"sim": sim_handler}


def main(args: argparse.Namespace):
    async_task_wrapper(args.job_id, args.route_name, routes[args.route_name])


def cli(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser("job", description="CLI for C/S jobs.")
    parser.add_argument("--job-id", "-t", required=True)
    parser.add_argument("--route-name", "-r", required=True)
    parser.set_defaults(func=main)
