import argparse
import os

from cs_workers.services import manage, scheduler, outputs_processor
from cs_workers.clients import publish
from cs_workers.executors import job, api_task

TAG = os.environ.get("TAG", "")
PROJECT = os.environ.get("PROJECT", "cs-workers-dev")


def cli():
    parser = argparse.ArgumentParser(description="C/S Workers CLI")
    parser.add_argument("--tag", required=False, default=TAG)
    parser.add_argument("--project", required=False, default=PROJECT)
    sub_parsers = parser.add_subparsers()

    manage.cli(sub_parsers)
    scheduler.cli(sub_parsers)
    outputs_processor.cli(sub_parsers)
    publish.cli(sub_parsers)
    job.cli(sub_parsers)
    api_task.cli(sub_parsers)

    args = parser.parse_args()
    args.func(args)
