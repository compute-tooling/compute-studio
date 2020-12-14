import argparse
import copy
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlparse
import warnings

import yaml

import cs_secrets
from .config import webapp_config

secret_vars = [
    "STRIPE_SECRET",
    "WEBHOOK_SECRET",
    "WEB_CS_CRYPT_KEY",
    "MAILGUN_API_KEY",
    "DJANGO_SECRET_KEY",
    "SENTRY_API_DSN",
]


def run(cmd):
    print(f"Running: {cmd}\n")
    s = time.time()
    res = subprocess.run(cmd, shell=True, check=True)
    f = time.time()
    print(f"\n\tFinished in {f-s} seconds.\n")
    return res


class Manager:
    cr = "gcr.io"

    def __init__(
        self, tag, use_kind=False, project=None, cs_url=None, kubernetes_target="-",
    ):
        self.tag = tag
        self.use_kind = use_kind
        self.project = project
        if cs_url is not None:
            self.host = urlparse(cs_url).netloc
        else:
            self.host = None
        self.kubernetes_target = kubernetes_target
        self.load_templates()

    def load_templates(self):
        with open(Path("web-kubernetes") / "secret.template.yaml") as f:
            self.secret_template = yaml.safe_load(f.read())

        with open(Path("web-kubernetes") / "web-deployment.template.yaml") as f:
            self.web_deployment_template = yaml.safe_load(f.read())

        with open(Path("web-kubernetes") / "web-service.yaml") as f:
            self.web_service = yaml.safe_load(f.read())

        with open(Path("web-kubernetes") / "web-configmap.yaml") as f:
            self.web_configmap = yaml.safe_load(f.read())

        with open(Path("web-kubernetes") / "web-serviceaccount.yaml") as f:
            self.web_serviceaccount = yaml.safe_load(f.read())

        with open(Path("web-kubernetes") / "deployment-cleanup.template.yaml") as f:
            self.deployment_cleanup_job_template = yaml.safe_load(f.read())

        with open(Path("web-kubernetes") / "web-ingressroute.template.yaml") as f:
            self.web_ingressroute = list(yaml.safe_load_all(f.read()))

        with open(Path("web-kubernetes") / "db-deployment.yaml") as f:
            self.db_deployment = yaml.safe_load(f.read())

        with open(Path("web-kubernetes") / "db-service.yaml") as f:
            self.db_service = yaml.safe_load(f.read())

    def build(self, dev=False):
        run(f"docker build -t webbase:latest -f Dockerfile.base ./")
        if dev:
            run(f"docker build -t web:{self.tag} -f Dockerfile.dev ./")
        else:
            run(f"docker build -t web:{self.tag} -f Dockerfile ./")

    def push(self):
        run(f"docker tag web:{self.tag} {self.web_image}")
        if self.use_kind:
            cmd_prefix = "kind load docker-image --name cs --nodes cs-worker3"
            run(f"{cmd_prefix} {self.web_image}")

        else:
            cmd_prefix = "docker push"
            run(f"{cmd_prefix} {self.web_image}")

    @property
    def web_image(self):
        return f"{self.cr}/{self.project}/web:{self.tag}"

    def config(self, update_db=False, dev=False):
        self.write_secret()
        self.write_web(dev=dev)
        if update_db:
            self.write_db()
        self.write_deployment_cleanup_job()

    def write_db(self):
        """
        Write database deployment.

        Currently only supports deploying as vanilla postgres mounted on a volume:

        - local volume:
            db:
              provider: volume
              args:
                - volumes:
                  - name: db-volume
                    hostPath:
                      path: /db-data
                      type: Directory
        """
        db_deployment = self.db_deployment
        db_config = {}
        for var in ["db", "web-db"]:
            db_config = webapp_config.get(var, {})
            if db_config:
                break
        assert (
            db_config.get("provider") == "volume"
        ), f"Got: {db_config.get('provider', None)}"
        args = db_config["args"][0]
        db_deployment["spec"]["template"]["spec"]["volumes"] = args["volumes"]
        self.write_config(self.db_deployment, filename="db-deployment.yaml")
        self.write_config(self.db_service, filename="db-service.yaml")

    def write_web(self, dev=False):
        web_obj = copy.deepcopy(self.web_deployment_template)
        web_configmap = copy.deepcopy(self.web_configmap)
        spec = web_obj["spec"]["template"]["spec"]
        spec["containers"][0]["image"] = self.web_image

        for var in [
            "BUCKET",
            "DATABASE_URL",
            "DEFAULT_CLUSTER_USER",
            "DEFAULT_VIZ_HOST",
            "USE_STRIPE",
        ]:
            if webapp_config.get(var, None):
                web_configmap["data"][var] = webapp_config[var]

        if dev:
            warnings.warn("Web deployment is being created in DEBUG mode!")
            spec["containers"][0]["volumeMounts"] = [
                {"name": "code-volume", "mountPath": "/code"}
            ]
            spec["volumes"] = [
                {
                    "name": "code-volume",
                    "hostPath": {"path": "/code", "type": "Directory",},
                }
            ]
            web_configmap["data"]["DEBUG"] = "true"
            web_configmap["data"]["LOCAL"] = "true"
        if self.host is not None:
            web_ir = copy.deepcopy(self.web_ingressroute)
            # Set host on https and http ingressroutes.
            web_ir[0]["spec"]["routes"][0]["match"] = f"Host(`{self.host}`)"
            web_ir[1]["spec"]["routes"][0]["match"] = f"Host(`{self.host}`)"

        db_config = {}
        for var in ["db", "web-db"]:
            db_config = webapp_config.get(var, {})
            if db_config:
                break

        if db_config.get("provider", "") == "gcp-sql-proxy":
            spec["containers"].append(db_config["args"][0])

        if webapp_config.get("resources"):
            spec["containers"][0]["resources"] = webapp_config["resources"]

        if webapp_config.get("replicas"):
            web_obj["spec"]["replicas"] = webapp_config["replicas"]

        self.write_config(self.web_serviceaccount, filename="web-serviceaccount.yaml")
        self.write_config(web_obj, filename="web-deployment.yaml")
        self.write_config(self.web_service, filename="web-service.yaml")
        self.write_config(web_configmap, filename="web-configmap.yaml")
        if self.host is not None:
            self.write_config_all(web_ir, filename="web-ingressroute.yaml")

    def write_deployment_cleanup_job(self, dev=False):
        job_obj = copy.deepcopy(self.deployment_cleanup_job_template)
        spec = job_obj["spec"]["jobTemplate"]["spec"]["template"]["spec"]
        spec["containers"][0]["image"] = self.web_image

        if dev:
            warnings.warn("Deployment clean up job is being created in DEBUG mode!")
            spec["containers"][0]["volumeMounts"] = [
                {"name": "code-volume", "mountPath": "/code"}
            ]
            spec["volumes"] = [
                {
                    "name": "code-volume",
                    "hostPath": {"path": "/code", "type": "Directory",},
                }
            ]
        db_config = {}
        for var in ["db", "cronjob-db", "web-db"]:
            db_config = webapp_config.get(var, {})
            if db_config:
                break

        if db_config.get("provider", "") == "gcp-sql-proxy":
            spec["containers"].append(db_config["args"][0])

        self.write_config(job_obj, filename="deployment-cleanup-job.yaml")

    def write_secret(self):
        secret_obj = copy.deepcopy(self.secret_template)
        secrets = cs_secrets.Secrets(self.project)

        for var in secret_vars:
            if (val := os.environ.get(var)) is not None:
                warnings.warn(f"Getting value for {var} from environment.")
                secret_obj["stringData"][var] = val
            if (val := secrets.get_or_none(var)) is not None:
                secret_obj["stringData"][var] = val

        self.write_config(secret_obj, filename="websecret.yaml")

    def write_config(self, config, filename=None):
        if self.kubernetes_target == "-":
            sys.stdout.write(yaml.dump(config))
            sys.stdout.write("---")
            sys.stdout.write("\n")
        else:
            with open(f"{self.kubernetes_target}/{filename}", "w") as f:
                f.write(yaml.safe_dump(config))

    def write_config_all(self, configs, filename=None):
        if self.kubernetes_target == "-":
            sys.stdout.write(yaml.safe_dump_all(configs))
            sys.stdout.write("---")
            sys.stdout.write("\n")
        else:
            with open(f"{self.kubernetes_target}/{filename}", "w") as f:
                f.write(yaml.safe_dump_all(configs))


def manager_from_args(args: argparse.Namespace):
    return Manager(
        args.tag,
        getattr(args, "use_kind", False),
        project=args.project,
        cs_url=args.cs_url,
        kubernetes_target=getattr(args, "out", "-"),
    )


def build(args):
    manager = manager_from_args(args)
    manager.build(dev=args.dev)


def push(args):
    manager = manager_from_args(args)
    manager.push()


def config(args):
    manager = manager_from_args(args)
    manager.config(
        update_db=args.update_db, dev=args.dev,
    )


def cli(subparsers: argparse._SubParsersAction):
    dsc = "CLI for deploying Compute Studio."
    parser = subparsers.add_parser("webapp", description=dsc)
    subparsers = parser.add_subparsers()

    build_parser = subparsers.add_parser("build", description="Create docker images.")
    build_parser.add_argument(
        "--dev", action="store_true", help="Run with Django dev server."
    )
    build_parser.set_defaults(func=build)

    build_parser = subparsers.add_parser("push", description="Push docker images.")
    build_parser.add_argument("--use-kind", action="store_true")
    build_parser.set_defaults(func=push)

    config_parser = subparsers.add_parser(
        "config", description="Create kubernetes files."
    )
    config_parser.add_argument("--out", "-o")
    config_parser.add_argument("--update-db", action="store_true")
    config_parser.add_argument(
        "--dev",
        action="store_true",
        help="Maps local directory to code directory for development.",
    )

    config_parser.set_defaults(func=config)
