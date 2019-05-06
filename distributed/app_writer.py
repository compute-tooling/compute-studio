import argparse
import json
import re
import shutil
from pathlib import Path

from jinja2 import Template


def clean(word):
    return re.sub("[^0-9a-zA-Z]+", "*", word).lower()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Write tasks modules from template.")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    path = Path("docker-compose-apps")
    path.mkdir(exist_ok=True)
    shutil.rmtree(path / "*", ignore_errors=True)

    with open("docker-compose.template.yml", "r") as f:
        template_text = f.read()

    template = Template(template_text)

    with open(args.config, "r") as f:
        config = json.loads(f.read())

    ext_str = ""

    for obj in config:
        owner, title, sim_time_limit = obj["owner"], obj["title"], obj["sim_time_limit"]
        safeowner = clean(owner)
        safetitle = clean(title)
        out = f"docker-compose-apps/docker-compose.{safeowner}_{safetitle}.yml"
        ext_str += f" -f {out}"
        with open(out, "w") as f:
            f.write(
                template.render(
                    OWNER=owner,
                    TITLE=title,
                    SAFEOWNER=safeowner,
                    SAFETITLE=safetitle,
                    SIM_TIME_LIMIT=sim_time_limit,
                    **obj["environment"],
                )
            )

    print(ext_str)
