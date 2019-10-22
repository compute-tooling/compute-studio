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
    k8s_app_target = "kubernetes/apps"
    cr = "gcr.io"

    def __init__(self, config, tag, project, models=None):
        self.tag = tag
        self.project = project
        self.models = models if models and models[0] else None

        # ensure clean path.
        path = Path(self.k8s_app_target)
        path.mkdir(exist_ok=True)
        shutil.rmtree(path / "*", ignore_errors=True)

        with open(config, "r") as f:
            self.config = yaml.safe_load(f.read())

        with open("flask-deployment.template.yaml", "r") as f:
            self.flask_template = yaml.safe_load(f.read())

        with open("app-deployment.template.yaml", "r") as f:
            self.app_template = yaml.safe_load(f.read())

    def build(self):
        """
        Wrap all methods that build, tag, and push the images as well as
        write the k8s config fiels.
        """
        self.build_base_images()
        self.write_flask_deployment()
        self.build_apps()

    def apply(self):
        """
        Experimental. Apply k8s config files to existing k8s cluster.
        """
        run(f"kubectl apply -f {self.k8s_target}")
        run(f"kubectl apply -f {self.k8s_app_target}")

    def dry_run(self):
        self.write_flask_deployment()
        for app in self.config:
            for action in ["io", "sim"]:
                self.write_app_deployment(app, action)

    def build_base_images(self):
        """
        Build, tag, and push base images for the flask app and modeling apps.

        Note: distributed and celerybase are tagged as "latest." All other apps
        pull from either distributed:latest or celerybase:latest.
        """
        run("docker build -t distributed:latest -f dockerfiles/Dockerfile ./")
        run("docker build -t celerybase:latest -f dockerfiles/Dockerfile.celerybase ./")
        run(f"docker build -t flask:{self.tag} -f dockerfiles/Dockerfile.flask ./")

        for img_name in ["distributed", "celerybase"]:
            run(f"docker tag {img_name} {self.cr}/{self.project}/{img_name}:latest")
            run(f"docker push {self.cr}/{self.project}/{img_name}:latest")

        run(f"docker tag flask:{self.tag} {self.cr}/{self.project}/flask:{self.tag}")
        run(f"docker push {self.cr}/{self.project}/flask:{self.tag}")

    def write_flask_deployment(self):
        """
        Write flask deployment file. Only step is filling in the image uri.
        """
        flask_deployment = copy.deepcopy(self.flask_template)
        flask_deployment["spec"]["template"]["spec"]["containers"][0][
            "image"
        ] = f"gcr.io/{self.project}/flask:{self.tag}"

        with open(f"{self.k8s_target}/flask-deployment.yaml", "w") as f:
            f.write(yaml.dump(flask_deployment))

        return flask_deployment

    def build_apps(self):
        """
        Build, tag, and push images and write k8s config files
        for all apps in config. Filters out those not in models
        list, if applicable.
        """
        for app in self.config:
            if self.models and app["title"] not in self.models[0]:
                continue
            try:
                self.build_app_image(app)
            except Exception as e:
                print(
                    f"There was an error building: "
                    f"{app['title']}/{app['owner']}:{self.tag}"
                )
                print(e)
                continue

            for action in ["io", "sim"]:
                self.write_app_deployment(app, action)

    def build_app_image(self, app):
        """
        Build, tag, and pus the image for a single app.
        """
        safeowner = clean(app["owner"])
        safetitle = clean(app["title"])
        img_name = f"{safeowner}_{safetitle}_tasks"

        reg_url = "https://github.com"
        raw_url = "https://raw.githubusercontent.com"

        buildargs = dict(
            OWNER=app["owner"],
            TITLE=app["title"],
            BRANCH=app["branch"],
            SAFEOWNER=safeowner,
            SAFETITLE=safetitle,
            SIM_TIME_LIMIT=app["sim_time_limit"],
            REPO_URL=app["repo_url"],
            RAW_REPO_URL=app["repo_url"].replace(reg_url, raw_url),
            **app["env"],
        )

        buildargs_str = " ".join(
            [f"--build-arg {arg}={value}" for arg, value in buildargs.items()]
        )
        cmd = (
            f"docker build {buildargs_str} -t {img_name}:{self.tag} "
            f"-f dockerfiles/Dockerfile.tasks ./"
        )
        run(cmd)

        run(
            f"docker tag {img_name}:{self.tag} {self.cr}/{self.project}/{img_name}:{self.tag}"
        )
        run(f"docker push {self.cr}/{self.project}/{img_name}:{self.tag}")

    def write_app_deployment(self, app, action):
        """
        Write k8s config file for an app.

        Note: Dask uses a dot notation for specifying paths
            in their config. It could be helpful for us to
            do that, too.
        """
        app_deployment = copy.deepcopy(self.app_template)
        safeowner = clean(app["owner"])
        safetitle = clean(app["title"])
        name = f"{safeowner}-{safetitle}-{action}"

        if action == "io":
            resources = {
                "requests": {"cpu": "700m", "memory": "250Mi"},
                "limits": {"cpu": "1000m", "memory": "700Mi"},
            }
            affinity_size = ["small", "medium"]
        else:
            resources = {"requests": {"memory": "1000Mi", "cpu": "1000m"}}
            resources = dict(resources, **copy.deepcopy(app["resources"]))
            affinity_size = app.get("affinity", {}).get("size", ["small", "medium"])

        if not isinstance(affinity_size, list):
            affinity_size = [affinity_size]

        app_deployment["metadata"]["name"] = name
        app_deployment["spec"]["selector"]["matchLabels"]["app"] = name
        app_deployment["spec"]["template"]["metadata"]["labels"] = name
        if "affinity" in app:
            app_deployment["spec"]["template"]["spec"]["affinity"] = {
                "nodeAffinity": {
                    "requiredDuringSchedulingIgnoredDuringExecution": {
                        "nodeSelectorTerms": [
                            {
                                "matchExpressions": [
                                    # only size for now.
                                    {
                                        "key": "size",
                                        "operator": "In",
                                        "values": affinity_size,
                                    }
                                ]
                            }
                        ]
                    }
                }
            }

        container_config = app_deployment["spec"]["template"]["spec"]["containers"][0]

        container_config.update(
            dict(
                name=name,
                image=f"{self.cr}/{self.project}/{safeowner}_{safetitle}_tasks:{self.tag}",
                command=[f"./celery_{action}.sh"],
                args=[
                    app["owner"],
                    app["title"],
                ],  # TODO: pass safe names to docker file at build and run time
                resources=resources,
            )
        )

        container_config["env"].append({"name": "TITLE", "value": app["title"]})
        container_config["env"].append({"name": "OWNER", "value": app["owner"]})

        # TODO: write secrets to secret config files instead of env.
        if app.get("secret"):
            for var, val in app.get("secret", {}).items():
                container_config["env"].append({"name": var.upper(), "value": val})

        with open(f"{self.k8s_app_target}/{name}-deployment.yaml", "w") as f:
            f.write(yaml.dump(app_deployment))

        return app_deployment


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy C/S compute cluster.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--tag", required=False, default=TAG)
    parser.add_argument("--project", required=False, default=PROJECT)
    parser.add_argument("--models", nargs="+", type=str, required=False, default=None)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cluster = Cluster(
        config=args.config, tag=args.tag, project=args.project, models=args.models
    )

    if args.build:
        cluster.build()
    elif args.dry_run:
        cluster.dry_run()
