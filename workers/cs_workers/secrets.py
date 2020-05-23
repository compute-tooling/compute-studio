import argparse
import json


class SecretNotFound(Exception):
    pass


class Secrets:
    def __init__(self, project):
        self.project = project
        self.client = None

    def set_secret(self, name, value):
        return self._set_secret(name, value)

    def get_secret(self, name):
        return self._get_secret(name)

    def list_secrets(self):
        raise NotImplementedError()

    def delete_secret(self, name):
        return self._delete_secret(name)

    def _set_secret(self, name, value):
        client = self._client()
        try:
            self._get_secret(name)
        except SecretNotFound:
            proj_parent = client.project_path(self.project)
            client.create_secret(proj_parent, name, {"replication": {"automatic": {}}})

        secret_bytes = value.encode("utf-8")

        secret_parent = client.secret_path(self.project, name)

        return client.add_secret_version(secret_parent, {"data": secret_bytes})

    def _get_secret(self, name):
        from google.api_core import exceptions

        client = self._client()

        try:
            response = client.access_secret_version(
                f"projects/{self.project}/secrets/{name}/versions/latest"
            )

            return response.payload.data.decode("utf-8")
        except exceptions.NotFound:
            raise SecretNotFound()

    def _delete_secret(self, name):
        try:
            self._get_secret(name)
        except SecretNotFound:
            return

        client = self._client()
        name = client.secret_path(self.project, name)
        client.delete_secret(name)

    def _client(self):
        if self.client:
            return self.client

        from google.cloud import secretmanager

        self.client = secretmanager.SecretManagerServiceClient()
        return self.client


def get_secret(args: argparse.Namespace):
    secrets = Secrets(args.project)
    print(secrets.get_secret(args.secret_name))


def set_secret(args: argparse.Namespace):
    secrets = Secrets(args.project)
    secrets.set_secret(args.secret_name, args.secret_value)


def list_secrets(args: argparse.Namespace):
    secrets = Secrets(args.project)
    print(json.dumps(secrets.list_secrets(), indent=2))


def delete_secret(args: argparse.Namespace):
    secrets = Secrets(args.project)
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
