import argparse
import copy
import datetime
import os
from pathlib import Path

import yaml

from cs_workers.cli import cli as workers_cli
from cs_deploy.webapp import cli as webapp_cli
from cs_secrets.cli import cli as secrets_cli

defaults = dict(
    TAG=datetime.datetime.now().strftime("%Y-%m-%d"), PROJECT=None, CS_URL=None
)


def load_env():
    config = copy.deepcopy(defaults)

    path = Path("cs-config.yaml")
    if path.exists():
        with open(path, "r") as f:
            user_config = yaml.safe_load(f.read())["webapp"]
    else:
        user_config = {}

    for var in defaults:
        if os.environ.get(var):
            config[var] = os.environ.get(var)
        elif user_config.get(var):
            config[var] = user_config.get(var)
    return config


def cli():
    parser = argparse.ArgumentParser(
        "CLI for managing C/S Kubernetes cluster and services."
    )
    user_config = load_env()
    parser.add_argument(
        "--tag", "-t", default=user_config.get("TAG"),
    )
    parser.add_argument("--project", default=user_config.get("PROJECT"))
    parser.add_argument("--cs-url", default=user_config.get("CS_URL"))

    subparsers = parser.add_subparsers()

    workers_cli(subparsers=subparsers)
    webapp_cli(subparsers=subparsers)
    secrets_cli(subparsers=subparsers)

    args = parser.parse_args()
    args.func(args)
