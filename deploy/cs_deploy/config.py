import copy
import datetime
import os
from pathlib import Path

import yaml


config_file = os.environ.get("CS_CONFIG_PATH", "cs-config.yaml")


def load_webapp_config():
    defaults = dict(
        TAG=datetime.datetime.now().strftime("%Y-%m-%d"), PROJECT=None, CS_URL=None
    )

    config = copy.deepcopy(defaults)

    path = Path(config_file)
    if path.exists():
        with open(path, "r") as f:
            user_config = yaml.safe_load(f.read())["webapp"]
    else:
        user_config = {}

    for var in defaults.keys() | user_config.keys():
        if os.environ.get(var):
            config[var] = os.environ.get(var)
        elif user_config.get(var):
            config[var] = user_config.get(var)
    return config


def load_workers_config():
    defaults = dict(CS_API_TOKEN=None, BUCKET=None,)

    config = copy.deepcopy(defaults)

    path = Path(config_file)
    if path.exists():
        with open(path, "r") as f:
            user_config = yaml.safe_load(f.read())
            if "workers" in user_config:
                user_config = user_config["workers"]
    else:
        user_config = {}

    for var in [
        "CS_API_TOKEN",
        "BUCKET",
        "CLUSTER_HOST",
        "VIZ_HOST",
    ] | user_config.keys():
        if os.environ.get(var):
            config[var] = os.environ.get(var)
        elif user_config.get(var):
            config[var] = user_config.get(var)
    return config


webapp_config = load_webapp_config()
workers_config = load_workers_config()
