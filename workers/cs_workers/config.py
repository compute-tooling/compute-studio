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
from cs_workers.models.secrets import ModelSecrets

CURR_PATH = Path(os.path.abspath(os.path.dirname(__file__)))
BASE_PATH = CURR_PATH / ".." / ".."


class ModelConfig:
    def __init__(
        self, project, cs_url, base_branch="origin/master", quiet=False,
    ):
        self.cs_url = cs_url
        self.project = project
        self.base_branch = base_branch
        self.quiet = quiet
        self.projects = None

    def get_projects(self, models=None):
        projects = get_projects(self.cs_url)
        if models is not None:
            selected = {}
            for model in models:
                o, t = parse_owner_title(model)
                selected[(o, t)] = projects[(o, t)]
            projects = selected
        self.format_resources(projects)
        self.projects = projects
        return self.projects

    def format_resources(self, projects):
        for ot, project in projects.items():
            if not projects[ot].get("resources"):
                mem = float(project.pop("memory"))
                cpu = float(project.pop("cpu"))
                if cpu and mem:
                    project["resources"] = {
                        "requests": {"memory": f"{mem}G", "cpu": cpu},
                        "limits": {"memory": f"{math.ceil(mem * 1.2)}G", "cpu": cpu,},
                    }
        return projects

    def get_diffed_projects(self):
        try:
            r = Repo()
            files_with_diff = r.index.diff(r.commit(self.base_branch), paths="config")
        except InvalidGitRepositoryError:
            files_with_diff = []
        diffed_projects = []
        for config_file in files_with_diff:
            with open(config_file.a_path, "r") as f:
                c = yaml.safe_load(f.read())
            diffed_projects.append((c["owner"], c["title"]))
        return diffed_projects

    def _list_secrets(self, app):
        secret = ModelSecrets(app["owner"], app["title"], project=self.project)
        return secret.list_secrets()
