import argparse
import json

from cs_secrets import Secrets


def get_secret(args: argparse.Namespace):
    secrets = Secrets(args.project)
    print(secrets.get(args.secret_name))


def set_secret(args: argparse.Namespace):
    secrets = Secrets(args.project)
    secrets.set(args.secret_name, args.secret_value)


def list_secrets(args: argparse.Namespace):
    secrets = Secrets(args.project)
    print(json.dumps(secrets.list(), indent=2))


def delete_secret(args: argparse.Namespace):
    secrets = Secrets(args.project)
    secrets.delete(args.delete)


def cli(subparsers: argparse._SubParsersAction = None):
    dsc = "CLI for secrets."
    if subparsers is None:
        parser = argparse.ArgumentParser(dsc)
    else:
        parser = subparsers.add_parser("secrets", description=dsc)

    secrets_subparsers = parser.add_subparsers()

    get_parser = secrets_subparsers.add_parser("get")
    get_parser.add_argument("secret_name")
    get_parser.set_defaults(func=get_secret)

    set_parser = secrets_subparsers.add_parser("set")
    set_parser.add_argument("secret_name")
    set_parser.add_argument("secret_value")
    set_parser.set_defaults(func=set_secret)

    list_parser = secrets_subparsers.add_parser("list")
    list_parser.add_argument("--secret-name", "-s", required=False)
    list_parser.set_defaults(func=list_secrets)

    delete_parser = secrets_subparsers.add_parser("delete")
    delete_parser.add_argument("delete")
    delete_parser.set_defaults(func=delete_secret)

    if subparsers is None:
        args = parser.parse_args()
        args.func(args)
