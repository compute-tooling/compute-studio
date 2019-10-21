import argparse
import copy
import yaml
import os
import re
import shutil
import subprocess
from pathlib import Path

from jinja2 import Template


CONTAINER_REGISTRY = "gcr.io"
TAG = os.environ.get("TAG", "")
PROJECT = os.environ.get("PROJECT", "comp-workers")


def clean(word):
    return re.sub("[^0-9a-zA-Z]+", "", word).lower()


def run(cmd):
    return subprocess.run(cmd, shell=True, check=True)


def build_base_images(project, tag):
    run("docker build -t distributed:latest -f dockerfiles/Dockerfile ./")
    run("docker build -t celerybase:latest -f dockerfiles/Dockerfile.celerybase ./")
    run(f"docker build -t flask:{tag} -f dockerfiles/Dockerfile.flask ./")

    for img_name in ["distributed", "celerybase"]:
        run(f"docker tag {img_name} {CONTAINER_REGISTRY}/{project}/{img_name}:latest")
        run(f"docker push {CONTAINER_REGISTRY}/{project}/{img_name}:latest")

    run(f"docker tag flask:{tag} {CONTAINER_REGISTRY}/{project}/flask:{tag}")
    run(f"docker push {CONTAINER_REGISTRY}/{project}/flask:{tag}")


def build_app_images(obj, project, tag):
    safeowner = clean(obj["owner"])
    safetitle = clean(obj["title"])
    img_name = f"{safeowner}_{safetitle}_tasks"

    reg_url = "https://github.com"
    raw_url = "https://raw.githubusercontent.com"

    buildargs = dict(
        OWNER=obj["owner"],
        TITLE=obj["title"],
        BRANCH=obj["branch"],
        SAFEOWNER=safeowner,
        SAFETITLE=safetitle,
        SIM_TIME_LIMIT=obj["sim_time_limit"],
        REPO_URL=obj["repo_url"],
        RAW_REPO_URL=obj["repo_url"].replace(reg_url, raw_url),
        **obj["env"],
    )

    buildargs_str = " ".join(
        [f"--build-arg {arg}={value}" for arg, value in buildargs.items()]
    )
    cmd = (
        f"docker build {buildargs_str} -t {img_name}:{tag} "
        f"-f dockerfiles/Dockerfile.tasks ./"
    )
    run(cmd)

    tag = obj.get("TAG") or args.tag
    run(f"docker tag {img_name}:{tag} {CONTAINER_REGISTRY}/{project}/{img_name}:{tag}")
    run(f"docker push {CONTAINER_REGISTRY}/{project}/{img_name}:{tag}")


def write_k8s_config(kube_config, obj, project, tag, action):
    kube_config = copy.deepcopy(kube_config)
    safeowner = clean(obj["owner"])
    safetitle = clean(obj["title"])
    name = f"{safeowner}-{safetitle}-{action}"

    if action == "io":
        resources = {
            "requests": {"cpu": "700m", "memory": "250Mi"},
            "limits": {"cpu": "1000m", "memory": "700Mi"},
        }
        affinity_size = ["small", "medium"]
    else:
        resources = {"requests": {"memory": "1000Mi", "cpu": "1000m"}}
        resources = dict(resources, **copy.deepcopy(obj["resources"]))
        affinity_size = obj.get("affinity", {}).get("size", ["small", "medium"])

    if not isinstance(affinity_size, list):
        affinity_size = [affinity_size]

    kube_config["metadata"]["name"] = name
    kube_config["spec"]["selector"]["matchLabels"]["app"] = name
    kube_config["spec"]["template"]["metadata"]["labels"] = name
    if "affinity" in obj:
        kube_config["spec"]["template"]["spec"]["affinity"] = {
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

    container_config = kube_config["spec"]["template"]["spec"]["containers"][0]

    container_config.update(
        dict(
            name=name,
            image=f"{CONTAINER_REGISTRY}/{project}/{safeowner}_{safetitle}_tasks:{tag}",
            command=[f"./celery_{action}.sh"],
            args=[
                obj["owner"],
                obj["title"],
            ],  # TODO: pass safe names to docker file at build and run time
            resources=resources,
        )
    )

    container_config["env"].append({"name": "TITLE", "value": obj["title"]})
    container_config["env"].append({"name": "OWNER", "value": obj["owner"]})

    # TODO: write secrets to secret config files instead of env.
    if obj.get("secret"):
        for var, val in obj.get("secret", {}).items():
            container_config["env"].append({"name": var.upper(), "value": val})

    return kube_config


def read_config_files():
    with open(args.config, "r") as f:
        config = yaml.safe_load(f.read())

    with open("flask-deployment.template.yaml", "r") as f:
        flask_template = yaml.safe_load(f.read())

    with open("app-deployment.template.yaml", "r") as f:
        kube_template = yaml.safe_load(f.read())

    return config, flask_template, kube_template


def write_flask_deployment(flask_template):
    flask_template["spec"]["template"]["spec"]["containers"][0][
        "image"
    ] = f"gcr.io/{args.project}/flask:{args.tag}"

    with open("kubernetes/flask-deployment.yaml", "w") as f:
        f.write(yaml.dump(flask_template))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Write tasks modules from template.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--tag", required=False, default=TAG)
    parser.add_argument("--project", required=False, default=PROJECT)
    parser.add_argument("--models", nargs="+", type=str, required=False, default=None)
    args = parser.parse_args()

    path = Path("kubernetes/apps")
    path.mkdir(exist_ok=True)
    shutil.rmtree(path / "*", ignore_errors=True)

    config, flask_template, kube_template = read_config_files()

    write_flask_deployment(flask_template)

    build_base_images(args.project, args.tag)

    models = args.models if args.models and args.models[0] else None

    for obj in config:
        if models and obj["title"] not in models:
            continue
        safeowner = clean(obj["owner"])
        safetitle = clean(obj["title"])

        try:
            build_app_images(obj, args.project, args.tag)
        except Exception as e:
            print(
                f"There was an error building: {obj['title']}/{obj['owner']}:{args.tag}"
            )
            print(e)
            continue

        for action in ["io", "sim"]:
            kube_config = write_k8s_config(
                kube_template, obj, args.project, args.tag, action
            )
            name = f"{safeowner}-{safetitle}-{action}"
            kubeout = (
                f"kubernetes/test-apps/{safeowner}-{safetitle}-{action}-deployment.yaml"
            )

            with open(kubeout, "w") as f:
                f.write(yaml.dump(kube_config))
