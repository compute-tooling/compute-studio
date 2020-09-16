import argparse


def serve(args: argparse.Namespace):
    from cs_config import functions

    getattr(functions, args.server_name)()


def cli(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser(
        "model-serve", description="CLI for C/S model servers."
    )
    parser.add_argument("--server-name", "-t", required=True)
    parser.set_defaults(func=serve)
