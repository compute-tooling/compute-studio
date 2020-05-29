import argparse
import json
import os

from cs_workers.utils import clean
from cs_workers import secrets


class ModelSecrets(secrets.Secrets):
    def __init__(self, owner=None, title=None, name=None, project=None):
        if owner and title:
            self.owner = owner
            self.title = title
        else:
            self.owner, self.title = name.split("/")
        self.project = project
        self.safe_owner = clean(self.owner)
        self.safe_title = clean(self.title)
        super().__init__(project)

    def set_secret(self, name, value):
        secret_name = f"{self.safe_owner}_{self.safe_title}"
        try:
            secret_val = self.get_secret()
        except secrets.SecretNotFound:
            secret_val = {name: value}
            return super().set_secret(secret_name, json.dumps(secret_val))
        else:
            if secret_val is not None:
                secret_val[name] = value
            else:
                secret_val = {name: value}
            if value is None:
                secret_val.pop(name)

        return super().set_secret(secret_name, json.dumps(secret_val))

    def get_secret(self, name=None):
        secret_name = f"{self.safe_owner}_{self.safe_title}"
        try:
            secret = json.loads(super().get_secret(secret_name))
        except secrets.SecretNotFound:
            return {}

        if name and name in secret:
            return secret[name]
        elif name:
            return None
        else:
            return secret

    def list_secrets(self):
        return self.get_secret()

    def delete_secret(self, name):
        return self.set_secret(name, None)


def get_secret(args: argparse.Namespace):
    secrets = ModelSecrets(args.owner, args.title, args.names, args.project)
    print(secrets.get_secret(args.secret_name))


def set_secret(args: argparse.Namespace):
    secrets = ModelSecrets(args.owner, args.title, args.names, args.project)
    secrets.set_secret(args.secret_name, args.secret_value)


def list_secrets(args: argparse.Namespace):
    secrets = ModelSecrets(args.owner, args.title, args.names, args.project)
    print(json.dumps(secrets.list_secrets(), indent=2))


def delete_secret(args: argparse.Namespace):
    secrets = ModelSecrets(args.owner, args.title, args.names, args.project)
    secrets.delete_secret(args.delete)


def cli(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser("secrets", description="CLI for model secrets.")
    parser.add_argument("--owner", required=False)
    parser.add_argument("--title", required=False)

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
