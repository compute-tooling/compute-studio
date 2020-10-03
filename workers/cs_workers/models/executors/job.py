import argparse
import asyncio
import functools
import json
import os

import redis
import httpx

import cs_storage
from cs_workers.models.executors.task_wrapper import async_task_wrapper


def sim_handler(task_id, meta_param_dict, adjustment):
    from cs_config import functions

    outputs = functions.run_model(meta_param_dict, adjustment)
    print("got result")
    outputs = cs_storage.serialize_to_json(outputs)
    print("storing results")
    for i in range(3):
        try:
            resp = httpx.post(
                "http://outputs-processor/write/",
                json={"task_id": task_id, "outputs": outputs},
                timeout=120.0,
            )
            break
        except Exception as e:
            print(i, e)

    print("got resp", resp.status_code, resp.url)
    assert resp.status_code == 200, f"Got code: {resp.status_code}"
    return resp.json()


routes = {"sim": sim_handler}


def main(args: argparse.Namespace):
    asyncio.run(
        async_task_wrapper(
            args.job_id, args.route_name, routes[args.route_name], timeout=args.timeout
        )
    )


def cli(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser("job", description="CLI for C/S jobs.")
    parser.add_argument("--job-id", "-t", required=True)
    parser.add_argument("--route-name", "-r", required=True)
    parser.add_argument("--timeout", required=False, type=int)
    parser.set_defaults(func=main)
