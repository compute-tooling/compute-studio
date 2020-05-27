import argparse

from cs_workers import secrets


class ServicesSecrets(secrets.Secrets):
    pass


def get_secret(args: argparse.Namespace):
    secrets = ServicesSecrets(args.project)
    print(secrets.get_secret(args.secret_name))


def set_secret(args: argparse.Namespace):
    secrets = ServicesSecrets(args.project)
    secrets.set_secret(args.secret_name, args.secret_value)


def list_secrets(args: argparse.Namespace):
    secrets = ServicesSecrets(args.project)
    print(json.dumps(secrets.list_secrets(), indent=2))


def delete_secret(args: argparse.Namespace):
    secrets = ServicesSecrets(args.project)
    secrets.delete_secret(args.delete)


def cli(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser("secrets", description="CLI for svc secrets.")

    secrets_subparsers = parser.add_subparsers()

    get_parser = secrets_subparsers.add_parser("get")
    get_parser.add_argument("secret_name")
    get_parser.set_defaults(func=get_secret)

    set_parser = secrets_subparsers.add_parser("set")
    set_parser.add_argument("--secret-name", "-s", required=False)
    set_parser.add_argument("--secret-value", "-v", required=False)
    set_parser.set_defaults(func=set_secret)

    list_parser = secrets_subparsers.add_parser("list")
    list_parser.add_argument("--secret-name", "-s", required=False)
    list_parser.set_defaults(func=list_secrets)

    delete_parser = secrets_subparsers.add_parser("delete")
    delete_parser.add_argument("delete")
    delete_parser.set_defaults(func=delete_secret)
