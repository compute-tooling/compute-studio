import argparse
import asyncio

import cs_storage
from cs_jobs.task_wrapper import task_wrapper

try:
    from cs_config import functions
except ImportError:
    functions = None


def version(**task_kwargs):
    return {"version": functions.get_version()}


def defaults(meta_param_dict=None, **task_kwargs):
    return functions.get_inputs(meta_param_dict)


def parse(meta_param_dict, adjustment, errors_warnings):
    return functions.validate_inputs(meta_param_dict, adjustment, errors_warnings)


def sim(meta_param_dict, adjustment):
    outputs = functions.run_model(meta_param_dict, adjustment)
    print("got result")
    return cs_storage.serialize_to_json(outputs)


routes = {"version": version, "defaults": defaults, "parse": parse, "sim": sim}


def main(args: argparse.Namespace):
    asyncio.run(
        task_wrapper(args.callback_url, args.route_name, routes[args.route_name])
    )


def cli():
    parser = argparse.ArgumentParser(description="CLI for C/S jobs.")
    parser.add_argument("--callback-url", required=True)
    parser.add_argument("--route-name", required=True)
    args = parser.parse_args()
    main(args)
