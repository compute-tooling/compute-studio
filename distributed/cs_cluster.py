import argparse
import copy
import yaml
import os
import re
import shutil
import subprocess
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

    k8s_target = "kubernetes/"
    cr = "gcr.io"

    def __init__(self, tag, project):
        self.tag = tag
        self.project = project

        with open("templates/flask-deployment.template.yaml", "r") as f:
            self.flask_template = yaml.safe_load(f.read())

        with open("templates/outputs-processor-deployment.template.yaml", "r") as f:
            self.outputs_processor_template = yaml.safe_load(f.read())

        with open("templates/secret.template.yaml", "r") as f:
            self.secret_template = yaml.safe_load(f.read())

    def build(self):
        """
        Build, tag, and push base images for the flask app and modeling apps.

        Note: distributed and celerybase are tagged as "latest." All other apps
        pull from either distributed:latest or celerybase:latest.
        """
        run("docker build -t distributed:latest -f dockerfiles/Dockerfile ./")
        run(
            f"docker build -t outputs_processor:{self.tag} -f dockerfiles/Dockerfile.outputs_processor ./"
        )
        run(f"docker build -t flask:{self.tag} -f dockerfiles/Dockerfile.flask ./")

        run(f"docker tag distributed {self.cr}/{self.project}/distributed:latest")
        run(f"docker push {self.cr}/{self.project}/distributed:latest")

        run(
            f"docker tag outputs_processor:{self.tag} {self.cr}/{self.project}/outputs_processor:{self.tag}"
        )
        run(f"docker push {self.cr}/{self.project}/outputs_processor:{self.tag}")

        run(f"docker tag flask:{self.tag} {self.cr}/{self.project}/flask:{self.tag}")
        run(f"docker push {self.cr}/{self.project}/flask:{self.tag}")

    def make_config(self):
        self.write_flask_deployment()
        self.write_outputs_processor_deployment()
        self.write_secret()

    def write_flask_deployment(self):
        """
        Write flask deployment file. Only step is filling in the image uri.
        """
        deployment = copy.deepcopy(self.flask_template)
        deployment["spec"]["template"]["spec"]["containers"][0][
            "image"
        ] = f"gcr.io/{self.project}/flask:{self.tag}"

        with open(f"{self.k8s_target}/flask-deployment.yaml", "w") as f:
            f.write(yaml.dump(deployment))

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

        with open(f"{self.k8s_target}/outputs-processor-deployment.yaml", "w") as f:
            f.write(yaml.dump(deployment))

        return deployment

    def write_secret(self):
        secrets = copy.deepcopy(self.secret_template)
        secrets["stringData"]["CS_API_TOKEN"] = self._get_secret("CS_API_TOKEN")

        with open(f"{self.k8s_target}/secret.yaml", "w") as f:
            f.write(yaml.dump(secrets))

    def _get_secret(self, secret_name):
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(
            f"projects/{self.project}/secrets/{secret_name}/versions/latest"
        )

        return response.payload.data.decode("utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy C/S compute cluster.")
    parser.add_argument("--tag", required=False, default=TAG)
    parser.add_argument("--project", required=False, default=PROJECT)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--make-config", action="store_true")
    args = parser.parse_args()

    cluster = Cluster(tag=args.tag, project=args.project)

    if args.build:
        cluster.build()
    if args.make_config:
        cluster.make_config()
