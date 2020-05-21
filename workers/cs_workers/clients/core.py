import copy
import json
import os
import sys
import uuid
import yaml
from pathlib import Path

from git import Repo, InvalidGitRepositoryError


from cs_workers.utils import clean, run, parse_owner_title, read_github_file
from cs_workers.clients.model_secrets import ModelSecrets

CURR_PATH = Path(os.path.abspath(os.path.dirname(__file__)))
BASE_PATH = CURR_PATH / ".." / ".."


class Core:
    cr = "gcr.io"

    def __init__(self, project, tag=None, base_branch="origin/master", quiet=False):
        self.tag = tag
        self.project = project
        self.base_branch = base_branch
        self.quiet = quiet

    def get_config(self, models):
        config = {}
        for owner_title in models:
            owner, title = parse_owner_title(owner_title)
            if (owner, title) in config:
                continue
            else:
                config_file = (
                    BASE_PATH / Path("config") / Path(owner) / Path(f"{title}.yaml")
                )
                if config_file.exists():
                    with open(config_file, "r") as f:
                        contents = yaml.safe_load(f.read())
                        config[(contents["owner"], contents["title"])] = contents
                else:
                    config.update(self.get_config_from_remote([(owner, title)]))
        if not self.quiet and config:
            print("# Updating:")
            print("\n#".join(f"  {o}/{t}" for o, t in config.keys()))
        elif not self.quiet:
            print("# No changes detected.")
        return config

    def get_config_from_diff(self):
        try:
            r = Repo()
            files_with_diff = r.index.diff(r.commit(self.base_branch), paths="config")
        except InvalidGitRepositoryError:
            files_with_diff = []
        config = {}
        for config_file in files_with_diff:
            with open(config_file.a_path, "r") as f:
                c = yaml.safe_load(f.read())
            config[(c["owner"], c["title"])] = c
        return config

    def get_config_from_remote(self, models):
        config = {}
        for owner_title in models:
            owner, title = parse_owner_title(owner_title)
            content = read_github_file(
                "compute-tooling",
                "compute-studio-publish",
                "master",
                f"config/{owner}/{title}.yaml",
            )
            config[(owner, title)] = yaml.safe_load(content)
        return config

    def _resources(self, app, action=None):
        if action == "io":
            resources = {
                "requests": {"cpu": 0.7, "memory": "0.25G"},
                "limits": {"cpu": 1, "memory": "0.7G"},
            }
        else:
            resources = {"requests": {"memory": "1G", "cpu": 1}}
            resources = dict(resources, **copy.deepcopy(app["resources"]))
        return resources

    def _list_secrets(self, app):
        secret = ModelSecrets(app["owner"], app["title"], self.project)
        return secret.list_secrets()
