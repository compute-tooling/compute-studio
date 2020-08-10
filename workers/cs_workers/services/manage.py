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

from kubernetes import client as kclient, config as kconfig

from cs_workers.services.secrets import ServicesSecrets, cli as secrets_cli


CURR_PATH = Path(os.path.abspath(os.path.dirname(__file__)))
BASE_PATH = CURR_PATH / ".."


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


class Manager:
    """
    Deploy and manage Compute Studio compute cluster:
        - build, tag, and push the docker images for the flask app and
        compute.studio modeling apps.
        - write k8s config files for the scheduler deployment and the
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

    kubernetes_target = "-"
    cr = "gcr.io"

    def __init__(
        self,
        tag,
        project,
        bucket=None,
        kubernetes_target="kubernetes/",
        use_kind=False,
        cs_url=None,
        cs_api_token=None,
    ):
        self.tag = tag
        self.project = project
        self.bucket = bucket
        self.use_kind = use_kind
        self.cs_url = cs_url
        self._cs_api_token = cs_api_token

        kconfig.load_kube_config()

        if kubernetes_target is None:
            self.kubernetes_target = Manager.kubernetes_target
        else:
            self.kubernetes_target = kubernetes_target

        self.templates_dir = BASE_PATH / Path("templates")
        self.dockerfiles_dir = BASE_PATH / Path("dockerfiles")

        with open(
            self.templates_dir / "services" / "scheduler-Deployment.template.yaml", "r"
        ) as f:
            self.scheduler_template = yaml.safe_load(f.read())

        with open(
            self.templates_dir
            / "services"
            / "outputs-processor-Deployment.template.yaml",
            "r",
        ) as f:
            self.outputs_processor_template = yaml.safe_load(f.read())

        with open(
            self.templates_dir / "services" / "redis-master-Deployment.template.yaml",
            "r",
        ) as f:
            self.redis_master_template = yaml.safe_load(f.read())

        with open(self.templates_dir / "secret.template.yaml", "r") as f:
            self.secret_template = yaml.safe_load(f.read())

        self._redis_secrets = None
        self._secrets = None

    def build(self):
        """
        Build, tag, and push base images for the scheduler app.

        Note: distributed and celerybase are tagged as "latest." All other apps
        pull from either distributed:latest or celerybase:latest.
        """
        distributed = self.dockerfiles_dir / "Dockerfile"
        redis = self.dockerfiles_dir / "Dockerfile.redis"
        outputs_processor = self.dockerfiles_dir / "Dockerfile.outputs_processor"
        scheduler = self.dockerfiles_dir / "Dockerfile.scheduler"

        run(f"docker build -t distributed:latest -f {distributed} ./")
        run(f"docker build -t redis-python:{self.tag} -f {redis} ./")
        run(f"docker build -t outputs_processor:{self.tag} -f {outputs_processor} ./")
        run(f"docker build -t scheduler:{self.tag} -f {scheduler} ./")

    def push(self):
        run(f"docker tag distributed {self.cr}/{self.project}/distributed:latest")
        run(
            f"docker tag redis-python:{self.tag} {self.cr}/{self.project}/redis-python:{self.tag}"
        )

        run(
            f"docker tag outputs_processor:{self.tag} {self.cr}/{self.project}/outputs_processor:{self.tag}"
        )

        run(
            f"docker tag scheduler:{self.tag} {self.cr}/{self.project}/scheduler:{self.tag}"
        )

        if self.use_kind:
            cmd_prefix = "kind load docker-image --name cs --nodes cs-worker"
        else:
            cmd_prefix = "docker push"

        run(f"{cmd_prefix} {self.cr}/{self.project}/distributed:latest")
        run(f"{cmd_prefix} {self.cr}/{self.project}/redis-python:{self.tag}")
        run(f"{cmd_prefix} {self.cr}/{self.project}/outputs_processor:{self.tag}")
        run(f"{cmd_prefix} {self.cr}/{self.project}/scheduler:{self.tag}")

    def config(self):
        config_filenames = [
            "scheduler-Service.yaml",
            "scheduler-RBAC.yaml",
            "outputs-processor-Service.yaml",
            "redis-master-Service.yaml",
            "job-cleanup-Deployment.yaml",
            "job-cleanup-RBAC.yaml",
        ]
        for filename in config_filenames:
            with open(self.templates_dir / "services" / f"{filename}", "r") as f:
                configs = yaml.safe_load_all(f.read())
            for config in configs:
                name = config["metadata"]["name"]
                kind = config["kind"]
                self.write_config(f"{name}-{kind}.yaml", config)
        self.write_scheduler_deployment()
        self.write_outputs_processor_deployment()
        self.write_secret()
        self.write_redis_deployment()

        self.write_cloudflare_api_token()

    def write_scheduler_deployment(self):
        """
        Write scheduler deployment file. Only step is filling in the image uri.
        """
        deployment = copy.deepcopy(self.scheduler_template)
        deployment["spec"]["template"]["spec"]["containers"][0][
            "image"
        ] = f"gcr.io/{self.project}/scheduler:{self.tag}"
        self.write_config("scheduler-Deployment.yaml", deployment)

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

        self.write_config("outputs-processor-Deployment.yaml", deployment)

        return deployment

    def write_redis_deployment(self):
        deployment = copy.deepcopy(self.redis_master_template)
        container = deployment["spec"]["template"]["spec"]["containers"][0]
        container["image"] = f"gcr.io/{self.project}/redis-python:{self.tag}"
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
        self.write_config("redis-master-Deployment.yaml", deployment)

    def write_secret(self):
        assert self.bucket
        assert self.cs_url
        assert self.cs_api_token
        assert self.project
        secrets = copy.deepcopy(self.secret_template)
        secrets["stringData"]["CS_URL"] = self.cs_url
        secrets["stringData"]["CS_API_TOKEN"] = self.cs_api_token
        secrets["stringData"]["BUCKET"] = self.bucket
        secrets["stringData"]["PROJECT"] = self.project
        redis_secrets = self.redis_secrets()
        for name, sec in redis_secrets.items():
            if sec is not None:
                secrets["stringData"][name] = sec

        self.write_config("secret.yaml", secrets)

    def write_cloudflare_api_token(self):
        api_token = self.secrets.get_secret("CLOUDFLARE_API_TOKEN")

        secret = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {"name": "cloudflare-api-token-secret",},
            "type": "Opaque",
            "stringData": {"api-token": api_token},
        }

        self.write_config("cloudflare_token_secret.yaml", secret)

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
                value = self.secrets.get_secret(sec)
            except exceptions.NotFound:
                try:
                    value = redis_acl_genpass()
                    self.secrets.set_secret(sec, value)
                except Exception:
                    value = ""
            redis_secrets[sec] = value
        return redis_secrets

    @property
    def cs_api_token(self):
        if self._cs_api_token is None:
            self._cs_api_token = self.secrets._get_secret("CS_API_TOKEN")
        return self._cs_api_token

    @property
    def secrets(self):
        if self._secrets is None:
            self._secrets = ServicesSecrets(self.project)
        return self._secrets


def manager_from_args(args: argparse.Namespace):
    return Manager(
        tag=args.tag,
        project=args.project,
        bucket=args.bucket,
        kubernetes_target=getattr(args, "out", None),
        use_kind=getattr(args, "use_kind", None),
        cs_url=getattr(args, "cs_url", None),
        cs_api_token=getattr(args, "cs_api_token", None),
    )


def build(args: argparse.Namespace):
    cluster = manager_from_args(args)
    cluster.build()


def push(args: argparse.Namespace):
    cluster = manager_from_args(args)
    cluster.push()


def config(args: argparse.Namespace):
    cluster = manager_from_args(args)
    cluster.config()


def serve(args: argparse.Namespace):
    run("kubectl port-forward svc/scheduler 8888:80")


def cli(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser("services", aliases=["svc"])
    svc_subparsers = parser.add_subparsers()

    secrets_cli(svc_subparsers)

    build_parser = svc_subparsers.add_parser("build")
    build_parser.set_defaults(func=build)

    push_parser = svc_subparsers.add_parser("push")
    push_parser.add_argument("--use-kind", action="store_true")
    push_parser.set_defaults(func=push)

    config_parser = svc_subparsers.add_parser("config")
    config_parser.add_argument("--out", "-o")
    config_parser.set_defaults(func=config)

    serve_parser = svc_subparsers.add_parser("serve")
    serve_parser.set_defaults(func=serve)
