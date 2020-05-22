import argparse
import copy
import datetime
import os
from pathlib import Path
import random
import yaml

from cs_workers.services import manage, scheduler, outputs_processor
from cs_workers.clients import publish, model_secrets
from cs_workers.executors import job, api_task

TAG = os.environ.get("TAG", "")
PROJECT = os.environ.get("PROJECT", "cs-workers-dev")
CS_URL = os.environ.get("CS_URL", None)

defaults = dict(
    TAG=datetime.datetime.now().strftime("%Y-%m-%d"),
    PROJECT="cs-workers-dev",
    CS_URL=None,
    CS_API_TOKEN=None,
)


def load_env():
    config = copy.deepcopy(defaults)

    path = Path("cs-config.yaml")
    if path.exists():
        with open(path, "r") as f:
            user_config = yaml.safe_load(f.read())
    else:
        user_config = {}

    for var in ["TAG", "PROJECT", "CS_URL", "CS_API_TOKEN"]:
        if os.environ.get(var):
            config[var] = os.environ.get(var)
        elif user_config.get(var):
            config[var] = user_config.get(var)
    return config


def cli():
    config = load_env()
    parser = argparse.ArgumentParser(description="C/S Workers CLI")
    parser.add_argument("--tag", required=False, default=config["TAG"])
    parser.add_argument("--project", required=False, default=config["PROJECT"])
    parser.add_argument("--cs-url", required=False, default=config["CS_URL"])
    parser.add_argument(
        "--cs-api-token", required=False, default=config["CS_API_TOKEN"]
    )
    sub_parsers = parser.add_subparsers()

    manage.cli(sub_parsers)
    scheduler.cli(sub_parsers)
    outputs_processor.cli(sub_parsers)
    publish.cli(sub_parsers)
    job.cli(sub_parsers)
    api_task.cli(sub_parsers)
    model_secrets.cli(sub_parsers)

    args = parser.parse_args()
    args.func(args)
