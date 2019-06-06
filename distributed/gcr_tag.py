import argparse
import json
import re
import subprocess


def clean(word):
    return re.sub("[^0-9a-zA-Z]+", "", word).lower()


def run(cmd):
    return subprocess.run(cmd, shell=True, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tag built images as gcr.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--host", required=False, default="gcr.io")
    parser.add_argument("--project", required=False, default="comp-workers")
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()

    with open(args.config, "r") as f:
        config = json.loads(f.read())

    for obj in config:
        safeowner = clean(obj["owner"])
        safetitle = clean(obj["title"])
        img_name = f"{safeowner}_{safetitle}_tasks"
        run(
            f"docker tag comporg/{img_name}:{args.tag} {args.host}/{args.project}/{img_name}:{args.tag}"
        )
        run(f"docker push {args.host}/{args.project}/{img_name}:{args.tag}")
    for img_name in ["distributed", "celerybase"]:
        run(
            f"docker tag comporg/{img_name} {args.host}/{args.project}/{img_name}:latest"
        )
        run(f"docker push {args.host}/{args.project}/{img_name}:latest")

    run(
        f"docker tag comporg/flask:{args.tag} {args.host}/{args.project}/flask:{args.tag}"
    )
    run(f"docker push {args.host}/{args.project}/flask:{args.tag}")
