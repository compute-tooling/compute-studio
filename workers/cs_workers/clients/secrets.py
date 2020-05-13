import argparse
import json
import os

from cs_workers.utils import clean

PROJECT = os.environ.get("PROJECT", "cs-workers-dev")


class SecretNotFound(Exception):
    pass


class Secrets:
    def __init__(self, owner, title, project):
        self.owner = owner
        self.title = title
        self.project = project
        self.safe_owner = clean(owner)
        self.safe_title = clean(title)
        self.client = None

    def set_secret(self, name, value):
        return self._set_secret(name, value)

    def get_secret(self, name):
        return self._get_secret(name)

    def list_secrets(self):
        return self._get_secret()

    def delete_secret(self, name):
        return self._set_secret(name, None)

    def _set_secret(self, name, value):
        secret_name = f"{self.safe_owner}_{self.safe_title}"

        client = self._client()
        try:
            secret_val = self._get_secret()
        except SecretNotFound:
            secret_val = {name: value}
            proj_parent = client.project_path(self.project)
            client.create_secret(
                proj_parent, secret_name, {"replication": {"automatic": {}}}
            )
        else:
            if secret_val is not None:
                secret_val[name] = value
            else:
                secret_val = {name: value}
            if value is None:
                secret_val.pop(name)

        secret_bytes = json.dumps(secret_val).encode("utf-8")

        secret_parent = client.secret_path(self.project, secret_name)

        return client.add_secret_version(secret_parent, {"data": secret_bytes})

    def _get_secret(self, name=None):
        from google.api_core import exceptions

        secret_name = f"{self.safe_owner}_{self.safe_title}"

        client = self._client()

        try:
            response = client.access_secret_version(
                f"projects/{self.project}/secrets/{secret_name}/versions/latest"
            )

            secret = json.loads(response.payload.data.decode("utf-8"))
        except exceptions.NotFound:
            raise SecretNotFound()

        if name and name in secret:
            return secret[name]
        elif name:
            return None
        else:
            return secret

    def _client(self):
        if self.client:
            return self.client

        from google.cloud import secretmanager

        self.client = secretmanager.SecretManagerServiceClient()
        return self.client


def handle(args: argparse.Namespace):
    secrets = Secrets(args.owner, args.title, args.project)
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
    parser.add_argument("--project", required=False, default=PROJECT)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--secret-name", "-s")
    parser.add_argument("--secret-value", "-v")
    parser.add_argument("--list", "-l", action="store_true")
    parser.add_argument("--delete", "-d")
    parser.set_defaults(func=handle)
