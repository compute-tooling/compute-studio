import argparse
import json
import re
import os

from jinja2 import Template


def clean(word):
    return re.sub("[^0-9a-zA-Z]+", "", word).lower()


def template(owner, title, sim_time_limit, out):
    owner = clean(owner)
    title = clean(title)
    print(owner, title)
    with open("tasks_template.py") as f:
        text = f.read()

    t = Template(text)

    r = t.render(APP_NAME=f"{owner}_{title}_tasks", SIM_TIME_LIMIT=sim_time_limit)

    with open(os.path.join(out, f"{owner}_{title}_tasks.py"), "w") as f:
        f.write(r)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Write tasks modules from template.")
    parser.add_argument("--owner")
    parser.add_argument("--title")
    parser.add_argument("--sim-time-limit", dest="sim_time_limit", type=int)
    parser.add_argument("--config")
    parser.add_argument("--out", "-o", default="api/celery_app")
    args = parser.parse_args()

    if args.config:
        with open(args.config) as f:
            config = json.loads(f.read())
        for obj in config:
            template(obj["owner"], obj["title"], obj["sim_time_limit"], args.out)
    elif args.owner and args.title and args.sim_time_limit:
        template(args.owner, args.title, args.sim_time_limit, args.out)
    else:
        print("No arguments received.")
