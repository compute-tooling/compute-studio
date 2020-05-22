import argparse
import json
import os

from cs_workers.utils import clean
from cs_workers.secrets import Secrets, SecretNotFound

PROJECT = os.environ.get("PROJECT", "cs-workers-dev")


class ModelSecrets(Secrets):
    def __init__(self, owner, title, project):
        self.owner = owner
        self.title = title
        self.project = project
        self.safe_owner = clean(owner)
        self.safe_title = clean(title)
        super().__init__(project)

    def set_secret(self, name, value):
        secret_name = f"{self.safe_owner}_{self.safe_title}"
        try:
            secret_val = self.get_secret()
        except SecretNotFound:
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
        except SecretNotFound:
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


def handle(args: argparse.Namespace):
    secrets = ModelSecrets(args.owner, args.title, args.project)
    if args.secret_name and args.secret_value:
        secrets.set_secret(args.secret_name, args.secret_value)
    elif args.secret_name:
        print(secrets.get_secret(args.secret_name))
    elif args.delete:
        secrets.delete_secret(args.delete)

    if args.list:
        print(json.dumps(secrets.list_secrets(), indent=2))


def cli(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser("secrets", description="CLI for model secrets.")
    parser.add_argument("--owner", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--secret-name", "-s")
    parser.add_argument("--secret-value", "-v")
    parser.add_argument("--list", "-l", action="store_true")
    parser.add_argument("--delete", "-d")
    parser.set_defaults(func=handle)
