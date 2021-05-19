import argparse
from pathlib import Path

from cs_deploy.config import workers_config as config
import cs_workers.services.manage

import cs_workers.services.outputs_processor
import cs_workers.models.manage


def cli(subparsers: argparse._SubParsersAction = None):
    dsc = "CLI for deploying Compute Studio."
    if subparsers is None:
        parser = argparse.ArgumentParser(dsc)
    else:
        parser = subparsers.add_parser("workers", description=dsc)

    parser.add_argument("--bucket", required=False, default=config["BUCKET"])
    parser.add_argument(
        "--cs-api-token", required=False, default=config["CS_API_TOKEN"]
    )
    parser.add_argument("--viz-host", required=False, default=config.get("VIZ_HOST"))
    sub_parsers = parser.add_subparsers()

    cs_workers.services.manage.cli(sub_parsers, config=config)
    cs_workers.models.manage.cli(sub_parsers)

    if subparsers is None:
        args = parser.parse_args()
        args.func(args)
