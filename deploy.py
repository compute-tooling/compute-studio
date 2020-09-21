import argparse
import copy
import datetime
import os
from pathlib import Path
import subprocess
import sys
import time

import yaml

import cs_secrets


defaults = dict(TAG=datetime.datetime.now().strftime("%Y-%m-%d"), PROJECT=None)

secret_vars = [
    "STRIPE_SECRET",
    "WEBHOOK_SECRET",
    "WEB_CS_CRYPT_KEY",
    "MAILGUN_API_KEY",
    "POSTGRES_PASSWORD",
    "DJANGO_SECRET_KEY",
]


def load_env():
    config = copy.deepcopy(defaults)

    user_config = {}

    for var in defaults:
        if os.environ.get(var):
            config[var] = os.environ.get(var)
        elif user_config.get(var):
            config[var] = user_config.get(var)
    return config


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
        self, tag, use_kind=False, project=None, kubernetes_target="-",
    ):
        self.tag = tag
        self.use_kind = use_kind
        self.project = project
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

        with open(Path("web-kubernetes") / "db-deployment.yaml") as f:
            self.db_deployment = yaml.safe_load(f.read())

        with open(Path("web-kubernetes") / "db-service.yaml") as f:
            self.db_service = yaml.safe_load(f.read())

    def build(self):
        run(f"docker build -t webbase:latest -f Dockerfile.base ./")
        run(f"docker build -t web:{self.tag} -f Dockerfile.dev ./")

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

    def config(self):
        self.write_secret()
        self.write_web()
        self.write_postgres()

    def write_postgres(self):
        self.write_config(self.db_deployment, filename="db-deployment.yaml")
        self.write_config(self.db_service, filename="db-service.yaml")

    def write_web(self):
        web_obj = copy.deepcopy(self.web_deployment_template)
        web_obj["spec"]["template"]["spec"]["containers"][0]["image"] = self.web_image

        self.write_config(web_obj, filename="web-deployment.yaml")
        self.write_config(self.web_service, filename="web-service.yaml")
        self.write_config(self.web_configmap, filename="web-configmap.yaml")

    def write_secret(self):
        secret_obj = copy.deepcopy(self.secret_template)
        secrets = cs_secrets.Secrets(self.project)

        for var in secret_vars:
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
                f.write(yaml.dump(config))


def manager_from_args(args: argparse.Namespace):
    return Manager(
        args.tag,
        getattr(args, "use_kind", False),
        project=args.project,
        kubernetes_target=getattr(args, "out", "-"),
    )


def build(args):
    manager = manager_from_args(args)
    manager.build()


def push(args):
    manager = manager_from_args(args)
    manager.push()


def config(args):
    manager = manager_from_args(args)
    manager.config()


def cli():
    parser = argparse.ArgumentParser(
        "CLI for deploying Compute Studio with Kubernetes."
    )
    user_config = load_env()
    parser.add_argument(
        "--tag", "-t", default=user_config.get("TAG"),
    )
    parser.add_argument("--project", default=user_config.get("PROJECT"))
    subparsers = parser.add_subparsers()

    build_parser = subparsers.add_parser("build", description="Create docker images.")
    build_parser.set_defaults(func=build)

    build_parser = subparsers.add_parser("push", description="Push docker images.")
    build_parser.add_argument("--use-kind", action="store_true")
    build_parser.set_defaults(func=push)

    config_parser = subparsers.add_parser(
        "config", description="Create kubernetes files."
    )
    config_parser.add_argument("--out", "-o")
    config_parser.set_defaults(func=config)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    cli()
