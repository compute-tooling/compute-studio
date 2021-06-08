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

from cs_deploy.config import workers_config
from cs_workers.services.secrets import ServicesSecrets

# from cs_workers.services import scheduler

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
        - write k8s config files for the workers_api deployment and the
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
        cluster_host=None,
        viz_host=None,
    ):
        self.tag = tag
        self.project = project
        self.bucket = bucket
        self.use_kind = use_kind
        self.cluster_host = cluster_host
        self.viz_host = viz_host

        if kubernetes_target is None:
            self.kubernetes_target = Manager.kubernetes_target
        else:
            self.kubernetes_target = kubernetes_target

        self.templates_dir = BASE_PATH / Path("templates")
        self.dockerfiles_dir = BASE_PATH / Path("dockerfiles")

        self._redis_secrets = None
        self._secrets = None

    def build(self):
        """
        Build, tag, and push base images for the workers_api app.

        Note: distributed and celerybase are tagged as "latest." All other apps
        pull from either distributed:latest or celerybase:latest.
        """
        distributed = self.dockerfiles_dir / "Dockerfile"
        outputs_processor = self.dockerfiles_dir / "Dockerfile.outputs_processor"
        workers_api = self.dockerfiles_dir / "Dockerfile.workers_api"

        run(f"docker build -t distributed:latest -f {distributed} ./")
        run(f"docker build -t outputs_processor:{self.tag} -f {outputs_processor} ./")
        run(f"docker build -t workers_api:{self.tag} -f {workers_api} ./")

    def push(self):
        run(f"docker tag distributed {self.cr}/{self.project}/distributed:latest")
        run(
            f"docker tag outputs_processor:{self.tag} {self.cr}/{self.project}/outputs_processor:{self.tag}"
        )
        run(
            f"docker tag workers_api:{self.tag} {self.cr}/{self.project}/workers_api:{self.tag}"
        )

        if self.use_kind:
            cmd_prefix = "kind load docker-image --name cs --nodes cs-worker"
        else:
            cmd_prefix = "docker push"

        run(f"{cmd_prefix} {self.cr}/{self.project}/distributed:latest")
        run(f"{cmd_prefix} {self.cr}/{self.project}/outputs_processor:{self.tag}")
        run(f"{cmd_prefix} {self.cr}/{self.project}/workers_api:{self.tag}")

    def config(self, update_redis=False, update_dns=False):
        if update_dns:
            self.write_cloudflare_api_token()

    def write_cloudflare_api_token(self):
        api_token = self.secrets.get("CLOUDFLARE_API_TOKEN")

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
        cluster_host=getattr(args, "cluster_host", None),
        viz_host=getattr(args, "viz_host", None),
    )


def build(args: argparse.Namespace):
    cluster = manager_from_args(args)
    cluster.build()


def push(args: argparse.Namespace):
    cluster = manager_from_args(args)
    cluster.push()


def config_(args: argparse.Namespace):
    cluster = manager_from_args(args)
    cluster.config(update_redis=args.update_redis, update_dns=args.update_dns)


def port_forward(args: argparse.Namespace):
    run("kubectl port-forward svc/workers_api 8888:80")


def serve(args: argparse.Namespace):
    # workers_api.run()
    pass


def cli(subparsers: argparse._SubParsersAction, config=None, **kwargs):
    parser = subparsers.add_parser("services", aliases=["svc"])
    svc_subparsers = parser.add_subparsers()

    build_parser = svc_subparsers.add_parser("build")
    build_parser.set_defaults(func=build)

    push_parser = svc_subparsers.add_parser("push")
    push_parser.add_argument("--use-kind", action="store_true")
    push_parser.set_defaults(func=push)

    config_parser = svc_subparsers.add_parser("config")
    config_parser.add_argument("--out", "-o")
    config_parser.add_argument("--update-redis", action="store_true")
    config_parser.add_argument(
        "--cluster-host", required=False, default=config.get("CLUSTER_HOST")
    )
    config_parser.add_argument("--update-dns", action="store_true")
    config_parser.set_defaults(func=config_)

    pf_parser = svc_subparsers.add_parser("port-forward")
    pf_parser.set_defaults(func=port_forward)

    serve_parser = svc_subparsers.add_parser("serve")
    serve_parser.set_defaults(func=serve)
