import argparse
import copy
import os
import sys
import yaml
from datetime import datetime
from dateutil.parser import parse as dateutil_parse
from pathlib import Path

import docker
import httpx

from cs_workers.utils import run, clean, parse_owner_title

from cs_workers.services.secrets import ServicesSecrets  # TODO
from cs_workers.config import ModelConfig
from cs_workers.models import secrets

CURR_PATH = Path(os.path.abspath(os.path.dirname(__file__)))
BASE_PATH = CURR_PATH / ".."


class BaseManager:
    def __init__(self, project, cs_url, cs_api_token):
        self.project = project
        self.cs_url = cs_url
        self._cs_api_token = cs_api_token

    @property
    def cs_api_token(self):
        if self._cs_api_token is None:
            svc_secrets = ServicesSecrets(self.project)
            self._cs_api_token = svc_secrets.get_secret("CS_API_TOKEN")
        return self._cs_api_token


class Manager(BaseManager):
    """
    Build, test, and publish docker images for Compute Studio:

    args:
        - config: configuration for the apps powering C/S.
        - tag: image version, defined as [c/s version].[mm][dd].[n]
        - project: GCP project that the compute cluster is under.
        - models (optional): only build a subset of the models in
        the config.

    """

    kubernetes_target = "-"

    def __init__(
        self,
        project,
        tag,
        models=None,
        base_branch="origin/master",
        cs_url=None,
        cs_api_token=None,
        kubernetes_target=None,
        use_kind=False,
        staging_tag=None,
        use_latest_tag=False,
        cr="gcr.io",
        ignore_ci_errors=False,
        quiet=False,
    ):
        self.config = ModelConfig(project, cs_url, base_branch, quiet)
        super().__init__(project, cs_url, cs_api_token)
        self.tag = tag
        self.models = models.split(",") if models else None
        self.base_branch = base_branch
        self.cr = cr

        self.kubernetes_target = kubernetes_target or self.kubernetes_target
        self.use_kind = use_kind

        self.staging_tag = staging_tag
        self.use_latest_tag = use_latest_tag

        self.ignore_ci_errors = ignore_ci_errors

        if self.kubernetes_target == "-":
            self.quiet = True
        elif not self.kubernetes_target.exists():
            os.mkdir(self.kubernetes_target)

        models = self.config.get_diffed_projects()
        if self.models:
            models += self.models

        self.projects = {}
        for ot, data in self.config.projects(models=models).items():
            o, t = parse_owner_title(ot)
            self.projects[(o, t)] = data

        self.dockerfiles_dir = BASE_PATH / "dockerfiles"

        self.errored = set()

        self.load_templates()

    def load_templates(self):
        with open(
            BASE_PATH
            / Path("templates")
            / "models"
            / Path("api-task-deployment.template.yaml"),
            "r",
        ) as f:
            self.api_task_template = yaml.safe_load(f.read())

        with open(
            BASE_PATH
            / Path("templates")
            / "models"
            / Path("api-task-service.template.yaml"),
            "r",
        ) as f:
            self.api_task_service_template = yaml.safe_load(f.read())

        with open(
            BASE_PATH / Path("templates") / "models" / Path("secret.template.yaml"), "r"
        ) as f:
            self.secret_template = yaml.safe_load(f.read())

    def build(self):
        self.apply_method_to_apps(method=self.build_app_image)

    def test(self):
        self.apply_method_to_apps(method=self.test_app_image)

    def push(self):
        self.apply_method_to_apps(method=self.push_app_image)

    def stage(self):
        self.apply_method_to_apps(method=self.stage_app)

    def promote(self):
        self.apply_method_to_apps(method=self.promote_app)

    def write_app_config(self):
        self.apply_method_to_apps(method=self.write_secrets)
        self.apply_method_to_apps(method=self._write_api_task)

    def apply_method_to_apps(self, method):
        """
        Build, tag, and push images and write k8s config files
        for all apps in config. Filters out those not in models
        list, if applicable.
        """
        for name, app in self.projects.items():
            if self.models and f"{name[0]}/{name[1]}" not in self.models:
                continue
            try:
                method(app)
            except Exception as e:
                if not self.ignore_ci_errors:
                    raise e
                print(
                    f"There was an error building: "
                    f"{app['owner']}/{app['title']}:{self.tag}"
                )
                import traceback as tb

                tb.print_exc()
                self.errored.add((app["owner"], app["title"]))
                continue

    def build_app_image(self, app):
        """
        Build, tag, and pus the image for a single app.
        """
        safeowner = clean(app["owner"])
        safetitle = clean(app["title"])
        img_name = f"{safeowner}_{safetitle}_tasks"

        repo_tag = os.environ.get("REPO_TAG") or app["repo_tag"]
        repo_url = os.environ.get("REPO_URL") or app["repo_url"]

        reg_url = "https://github.com"
        raw_url = "https://raw.githubusercontent.com"

        buildargs = dict(
            OWNER=app["owner"],
            TITLE=app["title"],
            REPO_TAG=repo_tag,
            REPO_URL=repo_url,
            RAW_REPO_URL=repo_url.replace(reg_url, raw_url),
        )

        buildargs_str = " ".join(
            [f"--build-arg {arg}={value}" for arg, value in buildargs.items()]
        )
        dockerfile = self.dockerfiles_dir / "Dockerfile.model"
        cmd = (
            f"docker build {buildargs_str} -t {img_name}:{self.tag} -f {dockerfile} ./"
        )
        run(cmd)

        assert self.cr is not None

        run(
            f"docker tag {img_name}:{self.tag} {self.cr}/{self.project}/{img_name}:{self.tag}"
        )

    def test_app_image(self, app):
        safeowner = clean(app["owner"])
        safetitle = clean(app["title"])
        img_name = f"{safeowner}_{safetitle}_tasks"
        cmd = ["py.test", "/home/test_functions.py", "-v", "-s"]
        secrets = self.config._list_secrets(app)
        client = docker.from_env()
        container = client.containers.run(
            f"{img_name}:{self.tag}", cmd, environment=secrets, detach=True
        )

        for line in container.logs(stream=True):
            line = line.decode()
            for name, value in secrets.items():
                line = line.replace(name, "******").replace(value, "******")
            print(line.strip("\n"))

        container.reload()
        exit_status = container.wait()
        if exit_status["StatusCode"] == 1:
            raise RuntimeError("Tests failed with exit status 1.")

    def push_app_image(self, app):
        assert self.cr is not None
        safeowner = clean(app["owner"])
        safetitle = clean(app["title"])
        img_name = f"{safeowner}_{safetitle}_tasks"
        if self.use_kind:
            cmd_prefix = "kind load docker-image --name cs --nodes cs-worker2"
        elif self.use_latest_tag:
            raise Exception("Unable to push latest tag for use outside of kind.")
        else:
            cmd_prefix = "docker push"

        if self.use_latest_tag:
            tag = self.get_latest_tag(app)
        else:
            tag = self.tag

        run(f"{cmd_prefix} {self.cr}/{self.project}/{img_name}:{tag}")

    def stage_app(self, app):
        resp = httpx.post(
            f"{self.config.cs_url}/apps/api/v1/{app['owner']}/{app['title']}/tags/",
            json={"staging_tag": self.staging_tag},
            headers={"Authorization": f"Token {self.cs_api_token}"},
        )
        assert (
            resp.status_code == 200
        ), f"Got: {resp.url} {resp.status_code} {resp.text}"

        sys.stdout.write(resp.json()["staging_tag"])

    def promote_app(self, app):
        resp = httpx.get(
            f"{self.config.cs_url}/apps/api/v1/{app['owner']}/{app['title']}/tags/",
            headers={"Authorization": f"Token {self.cs_api_token}"},
        )
        assert (
            resp.status_code == 200
        ), f"Got: {resp.url} {resp.status_code} {resp.text}"
        staging_tag = resp.json()["staging_tag"]
        resp = httpx.post(
            f"{self.config.cs_url}/apps/api/v1/{app['owner']}/{app['title']}/tags/",
            json={"latest_tag": staging_tag or self.tag, "staging_tag": None},
            headers={"Authorization": f"Token {self.cs_api_token}"},
        )
        assert (
            resp.status_code == 200
        ), f"Got: {resp.url} {resp.status_code} {resp.text}"

        sys.stdout.write(resp.json()["latest_tag"])

    def write_secrets(self, app):
        secret_config = copy.deepcopy(self.secret_template)
        safeowner = clean(app["owner"])
        safetitle = clean(app["title"])
        name = f"{safeowner}-{safetitle}-secret"

        secret_config["metadata"]["name"] = name

        for name, value in self.config._list_secrets(app).items():
            secret_config["stringData"][name] = value

        if not secret_config["stringData"]:
            secret_config["stringData"] = dict()

        if self.kubernetes_target == "-":
            sys.stdout.write(yaml.dump(secret_config))
            sys.stdout.write("---")
            sys.stdout.write("\n")
        else:
            with open(self.kubernetes_target / Path(f"{name}.yaml"), "w") as f:
                f.write(yaml.dump(secret_config))

        return secret_config

    def _write_api_task(self, app):
        if app["tech"] != "python-paramtools":
            return
        deployment = copy.deepcopy(self.api_task_template)
        safeowner = clean(app["owner"])
        safetitle = clean(app["title"])
        name = f"{safeowner}-{safetitle}-api-task"

        deployment["metadata"]["name"] = name
        deployment["spec"]["selector"]["matchLabels"]["app"] = name
        deployment["spec"]["template"]["metadata"]["labels"]["app"] = name

        container_config = deployment["spec"]["template"]["spec"]["containers"][0]

        if self.use_latest_tag:
            tag = self.get_latest_tag(app)
        else:
            tag = self.tag

        container_config.update(
            {
                "name": name,
                "image": f"{self.cr}/{self.project}/{safeowner}_{safetitle}_tasks:{tag}",
                "command": ["csw", "api-task", "--start"],
            }
        )

        container_config["env"] += [
            {"name": "exp_task_time", "value": str(app["exp_task_time"])},
            {
                "name": "REDIS_HOST",
                "valueFrom": {
                    "secretKeyRef": {"name": "worker-secret", "key": "REDIS_HOST"}
                },
            },
        ]

        self._set_secrets(app, container_config)

        service = copy.deepcopy(self.api_task_service_template)
        service["metadata"]["name"] = name
        service["spec"]["selector"]["app"] = name

        if self.kubernetes_target == "-":
            sys.stdout.write(yaml.dump(deployment))
            sys.stdout.write("---")
            sys.stdout.write("\n")
            sys.stdout.write(yaml.dump(service))
            sys.stdout.write("---")
            sys.stdout.write("\n")

        else:
            with open(
                self.kubernetes_target / Path(f"{name}-api-tasks-deployment.yaml"), "w"
            ) as f:
                f.write(yaml.dump(deployment))
            with open(
                self.kubernetes_target / Path(f"{name}-api-tasks-service.yaml"), "w"
            ) as f:
                f.write(yaml.dump(service))

        return deployment, service

    def _set_secrets(self, app, config):
        safeowner = clean(app["owner"])
        safetitle = clean(app["title"])
        name = f"{safeowner}-{safetitle}-secret"
        for key in self.config._list_secrets(app):
            config["env"].append(
                {"name": key, "valueFrom": {"secretKeyRef": {"name": name, "key": key}}}
            )

    def get_latest_tag(self, app):
        resp = httpx.get(
            f"{self.config.cs_url}/apps/api/v1/{app['owner']}/{app['title']}/tags/",
            headers={"Authorization": f"Token {self.cs_api_token}"},
        )
        assert (
            resp.status_code == 200
        ), f"Got: {resp.url} {resp.status_code} {resp.text}"
        return resp.json()["latest_tag"]


class DeploymentManager(BaseManager):
    def __init__(self, project, cs_url, cs_api_token=None, stale_after=3600):
        super().__init__(project, cs_url, cs_api_token)
        self.stale_after = stale_after
        self.client = httpx.Client(
            headers={"Authorization": f"Token {self.cs_api_token}"},
        )

    def get_deployments(self):
        resp = self.client.get(f"{self.cs_url}/apps/api/v1/deployments/")
        assert resp.status_code == 200, f"Got {resp.status_code}, {resp.text}"
        page = resp.json()
        results = page["results"]
        next_url = page["next"]
        while next_url is not None:
            resp = self.client.get(next_url)
            assert resp.status_code == 200, f"Got {resp.status_code}, {resp.text}"
            page = resp.json()

            results += page["results"]
            next_url = page["next"]

        return results

    def delete(self, project, name, dry_run=False):
        if dry_run:
            return
        resp = self.client.delete(
            f"{self.cs_url}/apps/api/v1/{project}/deployments/{name}/"
        )
        assert resp.status_code == 204, f"Got {resp.status_code} {resp.text}"

    def rm_stale(self, dry_run=False):
        for deployment in self.get_deployments():
            project = deployment["project"]
            name = deployment["name"]
            last_load_at = dateutil_parse(deployment["last_load_at"])
            last_ping_at = dateutil_parse(deployment["last_ping_at"])
            now = datetime.utcnow()

            load_secs_stale = (now - last_load_at.replace(tzinfo=None)).seconds
            ping_secs_stale = (now - last_ping_at.replace(tzinfo=None)).seconds

            secs_stale = min(load_secs_stale, ping_secs_stale)
            if secs_stale > self.stale_after:
                print(
                    f"Deleting {project} {name} since last use was {secs_stale} "
                    f"(> {self.stale_after}) seconds ago."
                )
                self.delete(project, name, dry_run=dry_run)


def build(args: argparse.Namespace):
    manager = Manager(
        project=args.project,
        tag=args.tag,
        cs_url=args.cs_url,
        models=args.names,
        base_branch=args.base_branch,
        cr=args.cr,
        ignore_ci_errors=args.ignore_ci_errors,
    )
    manager.build()


def test(args: argparse.Namespace):
    manager = Manager(
        project=args.project,
        tag=args.tag,
        cs_url=args.cs_url,
        models=args.names,
        base_branch=args.base_branch,
        cr=args.cr,
        ignore_ci_errors=args.ignore_ci_errors,
    )
    manager.test()


def push(args: argparse.Namespace):
    manager = Manager(
        project=args.project,
        tag=args.tag,
        cs_url=args.cs_url,
        models=args.names,
        base_branch=args.base_branch,
        use_kind=args.use_kind,
        cr=args.cr,
        cs_api_token=getattr(args, "cs_api_token", None),
        ignore_ci_errors=args.ignore_ci_errors,
        use_latest_tag=args.use_latest_tag,
    )
    manager.push()


def config(args: argparse.Namespace):
    manager = Manager(
        project=args.project,
        tag=args.tag,
        cs_url=args.cs_url,
        models=args.names,
        base_branch=args.base_branch,
        kubernetes_target=args.out,
        cr=args.cr,
        cs_api_token=getattr(args, "cs_api_token", None),
        ignore_ci_errors=args.ignore_ci_errors,
        use_latest_tag=args.use_latest_tag,
    )
    manager.write_app_config()


def promote(args: argparse.Namespace):
    manager = Manager(
        project=args.project,
        tag=args.tag,
        cs_url=args.cs_url,
        models=args.names,
        base_branch=args.base_branch,
        cr=args.cr,
        cs_api_token=getattr(args, "cs_api_token", None),
    )
    manager.promote()


def stage(args: argparse.Namespace):
    manager = Manager(
        project=args.project,
        tag=args.tag,
        cs_url=args.cs_url,
        models=args.names,
        base_branch=args.base_branch,
        cr=args.cr,
        cs_api_token=getattr(args, "cs_api_token", None),
        staging_tag=getattr(args, "staging_tag", None),
    )
    manager.stage()


def rm_stale_deployments(args: argparse.Namespace):
    manager = DeploymentManager(
        project=args.project,
        cs_url=args.cs_url,
        cs_api_token=args.cs_api_token,
        stale_after=args.stale_after,
    )
    manager.rm_stale(dry_run=args.dry_run)


def cli(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser(
        "models", description="Deploy and manage models on C/S compute cluster."
    )
    parser.add_argument("--names", "-n", type=str, required=False, default=None)
    parser.add_argument("--base-branch", default="origin/master", required=False)
    parser.add_argument("--cr", default="gcr.io", required=False)
    parser.add_argument("--ignore-ci-errors", action="store_true")
    model_subparsers = parser.add_subparsers()

    build_parser = model_subparsers.add_parser("build")
    build_parser.set_defaults(func=build)
    test_parser = model_subparsers.add_parser("test")
    test_parser.set_defaults(func=test)

    push_parser = model_subparsers.add_parser("push")
    push_parser.add_argument("--use-kind", action="store_true")
    push_parser.add_argument("--use-latest-tag", action="store_true")
    push_parser.set_defaults(func=push)

    config_parser = model_subparsers.add_parser("config")
    config_parser.add_argument("--use-latest-tag", action="store_true")
    config_parser.add_argument("--out", "-o", default=None)
    config_parser.set_defaults(func=config)

    stage_parser = model_subparsers.add_parser("stage")
    stage_parser.add_argument("staging_tag", type=str)
    stage_parser.set_defaults(func=stage)

    promote_parser = model_subparsers.add_parser("promote")
    promote_parser.set_defaults(func=promote)

    stale_deps_parser = model_subparsers.add_parser("rm-stale-deployments")
    stale_deps_parser.add_argument("--dry-run", action="store_true")
    stale_deps_parser.add_argument(
        "--stale-after", type=int, required=False, default=3600
    )
    stale_deps_parser.set_defaults(func=rm_stale_deployments)

    secrets.cli(model_subparsers)

    parser.set_defaults(func=lambda args: print(args))
