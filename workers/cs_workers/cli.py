import argparse

from cs_workers.services import manage, scheduler, outputs_processor
from cs_workers.clients import publish
from cs_workers.executors import job, api_task


def cli():
    parser = argparse.ArgumentParser(description="C/S Workers CLI")
    sub_parsers = parser.add_subparsers()

    manage.cli(sub_parsers)
    scheduler.cli(sub_parsers)
    outputs_processor.cli(sub_parsers)
    publish.cli(sub_parsers)
    job.cli(sub_parsers)
    api_task.cli(sub_parsers)

    args = parser.parse_args()
    args.func(args)
