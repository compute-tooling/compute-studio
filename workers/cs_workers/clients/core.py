import copy
import json
import math
import os
import sys
import uuid
import yaml
from pathlib import Path

from git import Repo, InvalidGitRepositoryError


from cs_workers.utils import (
    clean,
    run,
    parse_owner_title,
    read_github_file,
    get_projects,
)
from cs_workers.clients.model_secrets import ModelSecrets
from cs_workers.secrets import Secrets

CURR_PATH = Path(os.path.abspath(os.path.dirname(__file__)))
BASE_PATH = CURR_PATH / ".." / ".."


class Core:
    def __init__(
        self,
        project,
        cs_url,
        tag=None,
        base_branch="origin/master",
        quiet=False,
        cr="gcr.io",
        cs_api_token=None,
    ):
        self.tag = tag
        self.cs_url = cs_url
        self.project = project
        self.base_branch = base_branch
        self.quiet = quiet
        self.cr = cr
        self._cs_api_token = cs_api_token
        self.projects = None

    def merge_configs(self, config):
        if self.projects is None:
            self.projects = get_projects(self.cs_url)

        for ot in config:
            if (project := self.projects.get(ot)) :
                if not config[ot].get("resources"):
                    mem = float(project["memory"])
                    cpu = float(project["cpu"])
                    if cpu and mem:
                        config[ot]["resources"] = {
                            "requests": {"memory": mem, "cpu": cpu},
                            "limits": {"memory": math.ceil(mem * 1.2), "cpu": cpu,},
                        }
                for attr in ["repo_url", "repo_tag", "exp_task_time"]:
                    if not config.get(attr):
                        config[ot][attr] = project[attr]
        return config

    def get_config(self, models, merge=True):
        config = {}
        for owner_title in models:
            owner, title = parse_owner_title(owner_title)
            if (owner, title) in config:
                continue
            else:
                config_file = Path("config") / Path(owner) / Path(f"{title}.yaml")
                if config_file.exists():
                    with open(config_file, "r") as f:
                        contents = yaml.safe_load(f.read())
                        config[(contents["owner"], contents["title"])] = contents
                else:
                    config.update(
                        self.get_config_from_remote([(owner, title)], merge=False)
                    )
        if not self.quiet and config:
            print("# Updating:")
            print("\n#".join(f"#  {o}/{t}" for o, t in config.keys()))
        elif not self.quiet:
            print("# No changes detected.")
        if merge:
            return self.merge_configs(config)
        else:
            return config

    def get_config_from_diff(self, merge=True):
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
        if merge:
            return self.merge_configs(config)
        else:
            return config

    def get_config_from_remote(self, models, merge=True):
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
        if merge:
            return self.merge_configs(config)
        else:
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
        secret = ModelSecrets(app["owner"], app["title"], project=self.project)
        return secret.list_secrets()

    @property
    def cs_api_token(self):
        if self._cs_api_token is None:
            secrets = Secrets(self.project)
            self._cs_api_token = secrets.get_secret("CS_API_TOKEN")
        return self._cs_api_token
