import argparse
import json

import cs_secrets


class ServicesSecrets(cs_secrets.Secrets):
    pass


def get_secret(args: argparse.Namespace):
    secrets = ServicesSecrets(args.project)
    print(secrets.get(args.secret_name))


def set_secret(args: argparse.Namespace):
    secrets = ServicesSecrets(args.project)
    secrets.set(args.secret_name, args.secret_value)


def list_secrets(args: argparse.Namespace):
    secrets = ServicesSecrets(args.project)
    print(json.dumps(secrets.list(), indent=2))


def delete_secret(args: argparse.Namespace):
    secrets = ServicesSecrets(args.project)
    secrets.delete(args.delete)


def cli(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser("secrets", description="CLI for svc secrets.")

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
