import argparse
import json
import os
import re
import shutil
from pathlib import Path

from jinja2 import Template

TAG = os.environ.get("TAG", "")


def clean(word):
    return re.sub("[^0-9a-zA-Z]+", "", word).lower()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Write tasks modules from template.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--tag", required=False, default=TAG)
    args = parser.parse_args()

    path = Path("docker-compose-apps")
    path.mkdir(exist_ok=True)
    shutil.rmtree(path / "*", ignore_errors=True)

    with open("docker-compose.template.yml", "r") as f:
        dc_template_text = f.read()

    dc_template = Template(dc_template_text)

    with open(args.config, "r") as f:
        config = json.loads(f.read())

    with open("app-deployment.template.yaml", "r") as f:
        kube_template_text = f.read()

    kube_template = Template(kube_template_text)

    ext_str = ""
    reg_url = "https://github.com"
    raw_url = "https://raw.githubusercontent.com"
    for obj in config:
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
            kubeout = f"kubernetes/{safeowner}-{safetitle}-{action}-deployment.yaml"

            with open(kubeout, "w") as f:
                f.write(
                    kube_template.render(
                        OWNER=obj["owner"],
                        TITLE=obj["title"],
                        SAFEOWNER=safeowner,
                        SAFETITLE=safetitle,
                        ACTION=action,
                        TAG=args.tag,
                        **obj["environment"],
                    )
                )

    print(ext_str)
