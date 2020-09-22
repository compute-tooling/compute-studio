import argparse
import copy
import datetime
import os
from pathlib import Path

import yaml

from cs_workers.cli import cli as workers_cli
from cs_deploy.webapp import cli as webapp_cli
from cs_secrets.cli import cli as secrets_cli

from .config import webapp_config


def cli():
    parser = argparse.ArgumentParser(
        "CLI for managing C/S Kubernetes cluster and services."
    )
    user_config = webapp_config
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
