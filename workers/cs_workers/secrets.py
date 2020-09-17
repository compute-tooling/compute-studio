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
            parent = f"projects/{self.project}"
            client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": name,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
        parent = client.secret_path(self.project, name)
        secret_bytes = value.encode("utf-8")

        secret_parent = client.secret_path(self.project, name)

        return client.add_secret_version(
            request={"parent": secret_parent, "payload": {"data": secret_bytes}}
        )

    def _get_secret(self, name):
        from google.api_core import exceptions

        client = self._client()

        try:
            response = client.access_secret_version(
                request={
                    "name": f"projects/{self.project}/secrets/{name}/versions/latest"
                }
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

        from google.cloud import secretmanager_v1

        self.client = secretmanager_v1.SecretManagerServiceClient()

        return self.client
