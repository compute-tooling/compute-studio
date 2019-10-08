import argparse
import json
import os
import re
import subprocess

TAG = os.environ.get("TAG")


def clean(word):
    return re.sub("[^0-9a-zA-Z]+", "", word).lower()


def run(cmd):
    return subprocess.run(cmd, shell=True, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tag built images as gcr.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--host", required=False, default="gcr.io")
    parser.add_argument("--project", required=False, default="comp-studio")
    parser.add_argument("--tag", required=False, default=TAG)
    parser.add_argument("--models", nargs="+", type=str, required=False, default=None)
    args = parser.parse_args()

    with open(args.config, "r") as f:
        config = json.loads(f.read())

    for obj in config:
        if args.models and obj["title"] not in args.models:
            continue

        safeowner = clean(obj["owner"])
        safetitle = clean(obj["title"])
        img_name = f"{safeowner}_{safetitle}_tasks"
        tag = obj.get("TAG") or args.tag
        run(f"docker tag {img_name}:{tag} {args.host}/{args.project}/{img_name}:{tag}")
        run(f"docker push {args.host}/{args.project}/{img_name}:{tag}")
    for img_name in ["distributed", "celerybase"]:
        run(f"docker tag {img_name} {args.host}/{args.project}/{img_name}:latest")
        run(f"docker push {args.host}/{args.project}/{img_name}:latest")

    run(f"docker tag flask:{args.tag} {args.host}/{args.project}/flask:{args.tag}")
    run(f"docker push {args.host}/{args.project}/flask:{args.tag}")
