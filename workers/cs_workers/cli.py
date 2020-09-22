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
import cs_workers.models.executors.server

defaults = dict(CS_API_TOKEN=None, BUCKET=None,)


def load_env():
    config = copy.deepcopy(defaults)

    path = Path("cs-config.yaml")
    if path.exists():
        with open(path, "r") as f:
            user_config = yaml.safe_load(f.read())
            if "workers" in user_config:
                user_config = user_config["workers"]
    else:
        user_config = {}

    for var in [
        "CS_API_TOKEN",
        "BUCKET",
        "CLUSTER_HOST",
        "VIZ_HOST",
    ]:
        if os.environ.get(var):
            config[var] = os.environ.get(var)
        elif user_config.get(var):
            config[var] = user_config.get(var)
    return config


def cli(subparsers: argparse._SubParsersAction):
    dsc = "CLI for deploying Compute Studio."
    parser = subparsers.add_parser("workers", description=dsc)

    config = load_env()
    parser = argparse.ArgumentParser(description="C/S Workers CLI")
    parser.add_argument("--bucket", required=False, default=config["BUCKET"])
    parser.add_argument(
        "--cs-api-token", required=False, default=config["CS_API_TOKEN"]
    )
    parser.add_argument("--viz-host", required=False, default=config.get("VIZ_HOST"))
    sub_parsers = parser.add_subparsers()

    cs_workers.services.manage.cli(sub_parsers, config=config)
    cs_workers.services.scheduler.cli(sub_parsers)
    cs_workers.services.outputs_processor.cli(sub_parsers)
    cs_workers.models.manage.cli(sub_parsers)
    cs_workers.models.executors.job.cli(sub_parsers)
    cs_workers.models.executors.api_task.cli(sub_parsers)
    cs_workers.models.executors.server.cli(sub_parsers)
