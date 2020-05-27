import argparse
import copy
import datetime
import os
from pathlib import Path
import random
import yaml

import cs_workers.services.manage
import cs_workers.services.scheduler
import cs_workers.services.outputs_processor
import cs_workers.models.manage
import cs_workers.models.executors.job
import cs_workers.models.executors.api_task


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

    cs_workers.services.manage.cli(sub_parsers)
    cs_workers.services.scheduler.cli(sub_parsers)
    cs_workers.services.outputs_processor.cli(sub_parsers)
    cs_workers.models.manage.cli(sub_parsers)
    cs_workers.models.executors.job.cli(sub_parsers)
    cs_workers.models.executors.api_task.cli(sub_parsers)

    args = parser.parse_args()
    args.func(args)
