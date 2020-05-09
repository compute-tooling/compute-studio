import argparse
import copy
import yaml
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


TAG = os.environ.get("TAG", "")
PROJECT = os.environ.get("PROJECT", "cs-workers-dev")


def clean(word):
    return re.sub("[^0-9a-zA-Z]+", "", word).lower()


def run(cmd):
    print(f"Running: {cmd}\n")
    s = time.time()
    res = subprocess.run(cmd, shell=True, check=True)
    f = time.time()
    print(f"\n\tFinished in {f-s} seconds.\n")
    return res


def redis_acl_genpass():
    """
    Redis recommends using ACL GENPASS to generate passwords
    for ACL users. This function attempts to use a local
    redis installation to generate this password automatically.
    """
    import redis

    with redis.Redis(host="localhost", port=6379) as c:
        value = c.acl_genpass()

    return value


class Cluster:
    """
    Deploy and manage Compute Studio compute cluster:
        - build, tag, and push the docker images for the flask app and
        compute.studio modeling apps.
        - write k8s config files for the flask deployment and the
        compute.studio modeling app deployments.
        - apply k8s config files to an existing compute cluster.

        TODO:
        - teardown, update, add new models to cluster.

    args:
        - config: configuration for the apps powering C/S.
        - tag: image version, defined as [c/s version].[mm][dd].[n]
        - project: GCP project that the compute cluster is under.
        - models (optional): only build a subset of the models in
        the config.

    """

    kubernetes_target = "kubernetes/"
    cr = "gcr.io"

    def __init__(self, tag, project, kubernetes_target="kubernetes/"):
        self.tag = tag
        self.project = project

        if kubernetes_target is None:
            self.kubernetes_target = Cluster.kubernetes_target
        else:
            self.kubernetes_target = kubernetes_target

        with open("templates/flask-deployment.template.yaml", "r") as f:
            self.flask_template = yaml.safe_load(f.read())

        with open("templates/outputs-processor-deployment.template.yaml", "r") as f:
            self.outputs_processor_template = yaml.safe_load(f.read())

        with open("templates/redis-master-deployment.template.yaml", "r") as f:
            self.redis_master_template = yaml.safe_load(f.read())

        with open("templates/secret.template.yaml", "r") as f:
            self.secret_template = yaml.safe_load(f.read())

        self._redis_secrets = None

    def build(self):
        """
        Build, tag, and push base images for the flask app and modeling apps.

        Note: distributed and celerybase are tagged as "latest." All other apps
        pull from either distributed:latest or celerybase:latest.
        """
        run("docker build -t distributed:latest -f dockerfiles/Dockerfile ./")
        run("docker build -t redis-python:latest -f dockerfiles/Dockerfile.redis ./")
        run(
            f"docker build -t outputs_processor:{self.tag} -f dockerfiles/Dockerfile.outputs_processor ./"
        )
        run(f"docker build -t flask:{self.tag} -f dockerfiles/Dockerfile.flask ./")

        run(f"docker tag distributed {self.cr}/{self.project}/distributed:latest")

        run(
            f"docker tag outputs_processor:{self.tag} {self.cr}/{self.project}/outputs_processor:{self.tag}"
        )

        run(f"docker tag flask:{self.tag} {self.cr}/{self.project}/flask:{self.tag}")

    def push(self):
        run(f"docker tag distributed {self.cr}/{self.project}/distributed:latest")
        run(f"docker tag redis-python {self.cr}/{self.project}/redis-python:latest")

        run(
            f"docker tag outputs_processor:{self.tag} {self.cr}/{self.project}/outputs_processor:{self.tag}"
        )

        run(f"docker tag flask:{self.tag} {self.cr}/{self.project}/flask:{self.tag}")

        run(f"docker push {self.cr}/{self.project}/distributed:latest")
        run(f"docker push {self.cr}/{self.project}/redis-python:latest")
        run(f"docker push {self.cr}/{self.project}/outputs_processor:{self.tag}")
        run(f"docker push {self.cr}/{self.project}/flask:{self.tag}")

    def make_config(self):
        self.write_flask_deployment()
        self.write_outputs_processor_deployment()
        self.write_secret()
        self.write_redis_deployment()
        configs = [
            "flask-service.yaml",
            "outputs-processor-deployment.yaml",
            "outputs-processor-service.yaml",
            "redis-master-service.yaml",
        ]
        for filename in configs:
            with open(f"kubernetes/{filename}", "r") as f:
                config = yaml.safe_load(f.read())
            self.write_config(filename, config)

    def write_flask_deployment(self):
        """
        Write flask deployment file. Only step is filling in the image uri.
        """
        deployment = copy.deepcopy(self.flask_template)
        deployment["spec"]["template"]["spec"]["containers"][0][
            "image"
        ] = f"gcr.io/{self.project}/flask:{self.tag}"

        self.write_config("flask-deployment.yaml", deployment)

        return deployment

    def write_outputs_processor_deployment(self):
        """
        Write outputs processor deployment file. Only step is filling
        in the image uri.
        """
        deployment = copy.deepcopy(self.outputs_processor_template)
        deployment["spec"]["template"]["spec"]["containers"][0][
            "image"
        ] = f"gcr.io/{self.project}/outputs_processor:{self.tag}"

        self.write_config("outputs-processor-deployment.yaml", deployment)

        return deployment

    def write_redis_deployment(self):
        deployment = copy.deepcopy(self.redis_master_template)
        container = deployment["spec"]["template"]["spec"]["containers"][0]
        container["image"] = f"gcr.io/{self.project}/redis-python:latest"
        redis_secrets = self.redis_secrets()
        for name, sec in redis_secrets.items():
            if sec is not None:
                container["env"].append(
                    {
                        "name": name,
                        "valueFrom": {
                            "secretKeyRef": {"key": name, "name": "worker-secret"}
                        },
                    }
                )
        self.write_config("redis-master-deployment.yaml", deployment)

    def write_secret(self):

        secrets = copy.deepcopy(self.secret_template)
        secrets["stringData"]["CS_API_TOKEN"] = self._get_secret("CS_API_TOKEN")

        redis_secrets = self.redis_secrets()
        for name, sec in redis_secrets.items():
            if sec is not None:
                secrets["stringData"][name] = sec

        self.write_config("secret.yaml", secrets)

    def write_config(self, filename, config):
        if self.kubernetes_target == "-":
            sys.stdout.write(yaml.dump(config))
            sys.stdout.write("---")
            sys.stdout.write("\n")
        else:
            with open(f"{self.kubernetes_target}/{filename}", "w") as f:
                f.write(yaml.dump(config))

    def redis_secrets(self):
        """
        Return redis ACL user passwords. If they are not in the secret manager,
        try to generate them using a local instance of redis. If this fails,
        they are set to an empty string.
        """
        if self._redis_secrets is not None:
            return self._redis_secrets
        from google.api_core import exceptions

        redis_secrets = dict(
            REDIS_ADMIN_PW="", REDIS_EXECUTOR_PW="", REDIS_SCHEDULER_PW=""
        )
        for sec in redis_secrets:
            try:
                value = self._get_secret(sec)
            except exceptions.NotFound:
                try:
                    value = redis_acl_genpass()
                    self._set_secret(sec, value)
                except Exception:
                    value = ""
            redis_secrets[sec] = value
        return redis_secrets

    def _get_secret(self, secret_name):
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(
            f"projects/{self.project}/secrets/{secret_name}/versions/latest"
        )

        return response.payload.data.decode("utf-8")

    def _set_secret(self, name, value):
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        proj_parent = client.project_path(self.project)
        client.create_secret(proj_parent, name, {"replication": {"automatic": {}}})

        if not isinstance(value, bytes):
            value = value.encode("utf-8")

        secret_parent = client.secret_path(self.project, name)

        return client.add_secret_version(secret_parent, {"data": value})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy C/S compute cluster.")
    parser.add_argument("--tag", required=False, default=TAG)
    parser.add_argument("--project", required=False, default=PROJECT)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--push", action="store_true")
    parser.add_argument("--make-config", action="store_true")
    parser.add_argument("--config-out", "-o")
    args = parser.parse_args()

    cluster = Cluster(
        tag=args.tag, project=args.project, kubernetes_target=args.config_out
    )

    if args.build:
        cluster.build()
    if args.push:
        cluster.push()
    if args.make_config:
        cluster.make_config()
