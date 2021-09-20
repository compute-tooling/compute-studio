import copy
import json
import math
import os
import sys
import uuid
import yaml
from pathlib import Path

import httpx
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
        self,
        project,
        cs_url,
        *,
        cs_api_token=None,
        cs_auth_headers=None,
        base_branch="origin/master",
        quiet=False,
        rclient=None,
    ):
        self.cs_url = cs_url
        self.cs_api_token = cs_api_token
        self.cs_auth_headers = cs_auth_headers
        self.project = project
        self.base_branch = base_branch
        self.quiet = quiet
        self.rclient = rclient
        self._projects = None
        self._cluster_user = None

    @property
    def cluster_user(self):
        if self._cluster_user is not None:
            return self._cluster_user
        if self.cs_api_token is not None:
            resp = httpx.get(
                f"{self.cs_url}/users/status/",
                headers={"Authorization": f"Token {self.cs_api_token}"},
            )
            resp.raise_for_status()
            data = resp.json()
            self._cluster_user = data["username"]
        elif self.cs_auth_headers is not None:
            self._cluster_user = self.cs_auth_headers["Cluster-User"]
        else:
            # No use caching anon--this could be helpful if creds are updated
            # after creating the class.
            return "anon"

        return self._cluster_user

    def projects(self, models=None) -> dict:
        if self.rclient is not None:
            projects = self.rclient.hget("projects", self.cluster_user)
            if projects is None:
                self.set_projects(models=models)
                return self._projects
            else:
                self._projects = json.loads(projects.decode())
        else:
            self.set_projects(models=models)
        return self._projects

    def get_project(self, owner, title):
        return self.projects()[f"{owner}/{title}"]

    def set_projects(self, models=None, projects=None):
        if projects is None:
            projects = get_projects(
                self.cs_url, self.cs_api_token, self.cs_auth_headers
            )
        if models is not None:
            selected = {}
            for model in models:
                o, t = parse_owner_title(model)
                selected[f"{o}/{t}"] = projects[f"{o}/{t}"]
            projects = selected
        self.format_resources(projects)

        if self.rclient is not None:
            blob = self.rclient.hget("projects", self.cluster_user)
            if blob is not None:
                projects = {
                    **json.loads(blob.decode()),
                    **projects,
                }
            self.rclient.hset(
                "projects", self.cluster_user, json.dumps(projects),
            )
        self._projects = projects

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
        return secret.list()
