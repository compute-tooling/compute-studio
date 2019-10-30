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

        with open(config, "r") as f:
            self.config = yaml.safe_load(f.read())

        with open("templates/flask-deployment.template.yaml", "r") as f:
            self.flask_template = yaml.safe_load(f.read())

        with open("templates/sc-deployment.template.yaml", "r") as f:
            self.sc_template = yaml.safe_load(f.read())

        with open("templates/dask/scheduler-deployment.template.yaml", "r") as f:
            self.dask_scheduler_template = yaml.safe_load(f.read())

        with open("templates/dask/scheduler-service.template.yaml", "r") as f:
            self.dask_scheduler_service_template = yaml.safe_load(f.read())

        with open("templates/dask/worker-deployment.template.yaml", "r") as f:
            self.dask_worker_template = yaml.safe_load(f.read())

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
        # ensure clean path.
        path = Path(self.k8s_app_target)
        path.mkdir(exist_ok=True)
        stale_files = path.glob("*yaml")
        _ = [sf.unlink() for sf in stale_files]

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

            Also, all io (inputs) apps are deployed as a
            single-core cluster.
        """
        if action == "io":
            self.write_sc_app(app, action)
        elif app["cluster_type"] == "dask":
            self.write_dask_app(app, action)
        elif app["cluster_type"] == "single-core":
            self.write_sc_app(app, action)
        else:
            raise RuntimeError(f"Cluster type {app['cluster_type']} unknown.")

    def write_dask_app(self, app, action):
        self._write_dask_worker_app(app)
        self._write_dask_scheduler_app(app)
        self._write_dask_scheduler_service(app)

    def _write_dask_worker_app(self, app):
        app_deployment = copy.deepcopy(self.dask_worker_template)
        safeowner = clean(app["owner"])
        safetitle = clean(app["title"])
        name = f"{safeowner}-{safetitle}-dask-worker"
        image = f"{self.cr}/{self.project}/{safeowner}_{safetitle}_tasks:{self.tag}"

        app_deployment["metadata"]["name"] = name
        app_deployment["metadata"]["labels"]["app"] = name
        app_deployment["spec"]["replicas"] = app.get("replicas", 1)
        app_deployment["spec"]["selector"]["matchLabels"]["app"] = name
        app_deployment["spec"]["template"]["metadata"]["labels"]["app"] = name

        container_config = app_deployment["spec"]["template"]["spec"]["containers"][0]

        resources, _ = self._resources(app, action="sim")
        container_config.update(
            {
                "name": name,
                "image": image,
                "args": [
                    "dask-worker",
                    f"{safeowner}-{safetitle}-dask-scheduler:8786",
                    "--nthreads",
                    str(resources["limits"]["cpu"]),
                    "--memory-limit",
                    str(resources["limits"]["memory"]),
                    "--no-bokeh",
                ],
                "resources": resources,
            }
        )
        container_config["env"].append(
            {
                "name": "DASK_SCHEDULER_ADDRESS",
                "value": f"{safeowner}-{safetitle}-dask-scheduler:8786",
            }
        )

        self._set_secrets(app, container_config)

        with open(f"{self.k8s_app_target}/{name}-deployment.yaml", "w") as f:
            f.write(yaml.dump(app_deployment))

        return app_deployment

    def _write_dask_scheduler_app(self, app):
        app_deployment = copy.deepcopy(self.dask_scheduler_template)
        safeowner = clean(app["owner"])
        safetitle = clean(app["title"])
        name = f"{safeowner}-{safetitle}-dask-scheduler"
        image = f"{self.cr}/{self.project}/{safeowner}_{safetitle}_tasks:{self.tag}"

        app_deployment["metadata"]["name"] = name
        app_deployment["metadata"]["labels"]["app"] = name
        app_deployment["spec"]["selector"]["matchLabels"]["app"] = name
        app_deployment["spec"]["template"]["metadata"]["labels"]["app"] = name

        container_config = app_deployment["spec"]["template"]["spec"]["containers"][0]
        container_config.update({"name": name, "image": image})

        with open(f"{self.k8s_app_target}/{name}-deployment.yaml", "w") as f:
            f.write(yaml.dump(app_deployment))

        return app_deployment

    def _write_dask_scheduler_service(self, app):
        app_service = copy.deepcopy(self.dask_scheduler_service_template)
        safeowner = clean(app["owner"])
        safetitle = clean(app["title"])
        name = f"{safeowner}-{safetitle}-dask-scheduler"

        app_service["metadata"]["name"] = name
        app_service["metadata"]["labels"]["app"] = name
        app_service["spec"]["selector"]["app"] = name

        app_service["spec"]["ports"][0]["name"] = name
        app_service["spec"]["ports"][1]["name"] = f"{safeowner}-{safetitle}-dask-webui"

        with open(f"{self.k8s_app_target}/{name}-service.yaml", "w") as f:
            f.write(yaml.dump(app_service))

        return app_service

    def write_sc_app(self, app, action):
        app_deployment = copy.deepcopy(self.sc_template)
        safeowner = clean(app["owner"])
        safetitle = clean(app["title"])
        name = f"{safeowner}-{safetitle}-{action}"

        resources, affinity_size = self._resources(app, action)

        if not isinstance(affinity_size, list):
            affinity_size = [affinity_size]

        app_deployment["metadata"]["name"] = name
        app_deployment["spec"]["selector"]["matchLabels"]["app"] = name
        app_deployment["spec"]["template"]["metadata"]["labels"]["app"] = name
        if "affinity" in app and action == "sim":
            affinity_exp = {"key": "size", "operator": "In", "values": affinity_size}
            app_deployment["spec"]["template"]["spec"]["affinity"] = {
                "nodeAffinity": {
                    "requiredDuringSchedulingIgnoredDuringExecution": {
                        "nodeSelectorTerms": [{"matchExpressions": [affinity_exp]}]
                    }
                }
            }

        container_config = app_deployment["spec"]["template"]["spec"]["containers"][0]

        container_config.update(
            {
                "name": name,
                "image": f"{self.cr}/{self.project}/{safeowner}_{safetitle}_tasks:{self.tag}",
                "command": [f"./celery_{action}.sh"],
                "args": [
                    app["owner"],
                    app["title"],
                ],  # TODO: pass safe names to docker file at build and run time
                "resources": resources,
            }
        )

        container_config["env"].append({"name": "TITLE", "value": app["title"]})
        container_config["env"].append({"name": "OWNER", "value": app["owner"]})

        self._set_secrets(app, container_config)

        with open(f"{self.k8s_app_target}/{name}-deployment.yaml", "w") as f:
            f.write(yaml.dump(app_deployment))

        return app_deployment

    def _resources(self, app, action):
        if action == "io":
            resources = {
                "requests": {"cpu": 0.7, "memory": "0.25G"},
                "limits": {"cpu": 1, "memory": "0.7G"},
            }
            affinity_size = ["small", "medium"]
        else:
            resources = {"requests": {"memory": "1G", "cpu": 1}}
            resources = dict(resources, **copy.deepcopy(app["resources"]))
            affinity_size = app.get("affinity", {}).get("size", ["small", "medium"])
        return resources, affinity_size

    def _set_secrets(self, app, config):
        # TODO: write secrets to secret config files instead of env.
        if app.get("secret"):
            for var, val in app["secret"].items():
                config["env"].append({"name": var.upper(), "value": val})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy C/S compute cluster.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--tag", required=False, default=TAG)
    parser.add_argument("--project", required=False, default=PROJECT)
    parser.add_argument("--models", nargs="+", type=str, required=False, default=None)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--build-base-only", action="store_true")
    args = parser.parse_args()

    cluster = Cluster(
        config=args.config, tag=args.tag, project=args.project, models=args.models
    )

    if args.build:
        cluster.build()
    elif args.dry_run:
        cluster.dry_run()
    elif args.build_base_only:
        cluster.build_base_images()
