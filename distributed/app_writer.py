import argparse
import copy
import json
import os
import re
import shutil
from pathlib import Path

from jinja2 import Template

TAG = os.environ.get("TAG", "")
PROJECT = os.environ.get("PROJECT", "comp-workers")


def clean(word):
    return re.sub("[^0-9a-zA-Z]+", "", word).lower()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Write tasks modules from template.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--tag", required=False, default=TAG)
    parser.add_argument("--project", required=False, default=PROJECT)
    parser.add_argument("--models", nargs="+", type=str, required=False, default=None)
    args = parser.parse_args()

    path = Path("docker-compose-apps")
    path.mkdir(exist_ok=True)
    shutil.rmtree(path / "*", ignore_errors=True)

    path = Path("kubernetes/apps")
    path.mkdir(exist_ok=True)
    shutil.rmtree(path / "*", ignore_errors=True)

    with open("docker-compose.template.yml", "r") as f:
        dc_template_text = f.read()

    dc_template = Template(dc_template_text)

    with open(args.config, "r") as f:
        config = json.loads(f.read())

    with open("flask-deployment.template.yaml", "r") as f:
        flask_template_text = f.read()
    flask_template = Template(flask_template_text)
    with open("kubernetes/flask-deployment.yaml", "w") as f:
        f.write(flask_template.render(PROJECT=args.project, TAG=args.tag))

    with open("app-deployment.template.yaml", "r") as f:
        kube_template_text = f.read()

    kube_template = Template(kube_template_text)

    models = args.models if args.models and args.models[0] else None

    ext_str = ""
    reg_url = "https://github.com"
    raw_url = "https://raw.githubusercontent.com"

    for obj in config:
        if models and obj["title"] not in models:
            continue
        safeowner = clean(obj["owner"])
        safetitle = clean(obj["title"])
        repo_url = obj["repo_url"]
        raw_repo_url = repo_url.replace(reg_url, raw_url)
        out = f"docker-compose-apps/docker-compose.{safeowner}_{safetitle}.yml"
        ext_str += f" -f {out}"
        with open(out, "w") as f:
            f.write(
                dc_template.render(
                    OWNER=obj["owner"],
                    TITLE=obj["title"],
                    BRANCH=obj["branch"],
                    SAFEOWNER=safeowner,
                    SAFETITLE=safetitle,
                    SIM_TIME_LIMIT=obj["sim_time_limit"],
                    REPO_URL=repo_url,
                    RAW_REPO_URL=raw_repo_url,
                    **obj["environment"],
                )
            )
        for action in ["io", "sim"]:
            kubeout = (
                f"kubernetes/apps/{safeowner}-{safetitle}-{action}-deployment.yaml"
            )
            if action == "io":
                resources = {
                    "requests": {"cpu": "700m", "memory": "250Mi"},
                    "limits": {"cpu": "1000m", "memory": "700Mi"},
                }
            else:
                resources = {"requests": {"memory": "1000Mi", "cpu": "1000m"}}
                resources = dict(resources, **copy.deepcopy(obj["resources"]))

            with open(kubeout, "w") as f:
                f.write(
                    kube_template.render(
                        OWNER=obj["owner"],
                        TITLE=obj["title"],
                        PROJECT=args.project,
                        SAFEOWNER=safeowner,
                        SAFETITLE=safetitle,
                        ACTION=action,
                        TAG=obj.get("TAG") or args.tag,
                        REQUEST_MEMORY=resources["requests"]["memory"],
                        REQUEST_CPU=resources["requests"]["cpu"],
                        MAX_MEMORY=resources["limits"]["memory"],
                        MAX_CPU=resources["limits"]["cpu"],
                        **obj["environment"],
                    )
                )

    print(ext_str)
