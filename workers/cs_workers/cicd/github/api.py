"""
Wrapper for GitHub API.

Example Usage:

gh = GitHub(token)
repo = gh.repo("compute-tooling", "compute-studio-publish", primary_branch="master")

"""

import base64
from datetime import datetime
import os
from typing import List, Union

from dateutil import parser

import httpx


def filter_props(props, stop_val=None):
    if stop_val is None:
        return {name: value for name, value in props.items() if value is not stop_val}
    else:
        return {name: value for name, value in props.items() if value != stop_val}


def get_client(api_token=None):
    if api_token is None:
        api_token = os.environ.get("GITHUB_API_TOKEN")

    if api_token is None:
        return httpx.Client(base_url="https://api.github.com")

    return httpx.Client(
        headers={"Authorization": f"token {api_token}"},
        base_url="https://api.github.com",
    )


client = get_client()


class Repo:
    def __init__(self, owner, name, primary_branch="main"):
        self.owner = owner
        self.name = name
        self.primary_ref = Ref(self, primary_branch)

    def __str__(self):
        return f"{self.owner}/{self.name}"

    def __repr__(self):
        return str(self)

    def pull_request(self):
        return PullRequest(self)

    def create_ref(self, ref_name: str, parent: "Ref" = None) -> "Ref":
        parent = parent or self.primary_ref
        ref = Ref(self, name=ref_name, load_data=False)
        ref.create(parent=parent)
        return ref

    def get_ref(self, ref_name: str):
        return Ref(self, name=ref_name)

    def delete_ref(self, ref_name: str):
        return Ref(self, name=ref_name).delete()

    def workflow_runs(
        self, branch: "Ref" = None, event: str = None, status: str = None
    ):
        return WorkflowRun(self).list(branch=branch, event=event, status=status)

    def pull_requests(
        self,
        state: Union["open", "closed", "all"] = None,
        head: "Ref" = None,
        base: "Ref" = None,
        sort: Union["created", "updated", "popularity", "long-running"] = None,
        direct: Union["asc", "desc"] = None,
    ):
        return PullRequest(self).list(
            state=state, head=head, base=base, sort=sort, direct=direct
        )


class Ref:
    def __init__(
        self, repo: Repo, name: str, load_data: bool = True, head_sha: str = None
    ):
        self.repo = repo
        self.name = name
        self.data = {}
        self.head_sha = head_sha
        if load_data:
            self.load()

    def __str__(self):
        sha = self.head_sha or self.sha
        if sha is not None:
            sha = sha[:6]
        return f"{self.repo} @ {self.name} <{sha}>"

    def __repr__(self):
        return str(self)

    @property
    def sha(self):
        return self.data.get("object", {}).get("sha", None)

    def load(self):
        resp = client.get(
            f"/repos/{self.repo.owner}/{self.repo.name}/git/ref/heads/{self.name}",
        )
        resp.raise_for_status()
        self.data = resp.json()
        return self.data

    def create(self, parent: "Ref"):
        resp = client.post(
            f"/repos/{self.repo.owner}/{self.repo.name}/git/refs",
            json={"ref": f"refs/heads/{self.name}", "sha": parent.sha},
        )
        resp.raise_for_status()
        self.data = resp.json()
        return self.data

    def delete(self):
        resp = client.delete(
            f"/repos/{self.repo.owner}/{self.repo.name}/git/refs/heads/{self.name}",
        )
        resp.raise_for_status()

    def tree(self):
        return Tree(repo=self.repo, ref=self)


class Content:
    def __init__(self, repo: Repo, path: str, ref: Ref = None):
        self.repo = repo
        self.path = path
        self.ref = ref or repo.primary_ref
        self.load()

    @property
    def sha(self):
        return self.data.get("sha")

    @property
    def type_(self):
        return self.data.get("type")

    def __str__(self):
        return f"{self.repo.owner}/{self.repo.name}/blob/{self.ref.name}/{self.path}"

    def __repr__(self):
        return str(self)

    def get(self):
        resp = client.get(
            f"/repos/{self.repo.owner}/{self.repo.name}/contents/{self.path}?ref={self.ref.name}"
        )
        if resp.status_code == 404:
            raise FileNotFoundError(f"File not found: {str(self)}")

        resp.raise_for_status()
        return resp.json()

    def load(self):
        try:
            self.data = self.get()
        except FileNotFoundError:
            self.data = {}

    def exists(self):
        try:
            self.data = self.get()
        except FileNotFoundError:
            return False
        else:
            return True

    @property
    def content(self):
        if not self.data:
            self.load()
        if self.type_ != "file":
            raise TypeError(f"Unable to retrieve content for type {self.type_}")
        return base64.b64decode(self.data["content"]).decode("utf-8")

    def write(self, content: str, message: str = None):
        message = message or f"Updating {self.path}"
        resp = client.put(
            f"/repos/{self.repo.owner}/{self.repo.name}/contents/{self.path}",
            json={
                "message": message,
                "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
                "sha": self.sha,
                "branch": self.ref.name,
            },
        )
        resp.raise_for_status()
        self.load()
        return self

    def delete(self, message: str = None):
        message = message or f"Deleting {self.path}"
        resp = client.put(
            f"/repos/{self.repo.owner}/{self.repo.name}/contents/{self.path}",
            json={"message": message, "sha": self.sha, "branch": self.ref.name,},
        )
        if resp.status_code == 404:
            raise FileNotFoundError(f"File not found: {str(self)}")

        resp.raise_for_status()
        self.data = resp.json()
        return self.data


class MergeError(Exception):
    pass


class MergeConflictError(Exception):
    pass


class PullRequest:
    def __init__(self, repo: Repo, pull_number: int = None, data: dict = None):
        self.repo = repo
        self.pull_number = pull_number
        self.data = data or {}
        if pull_number is not None:
            self.load()

    def __str__(self):
        return f"{self.repo}#{self.pull_number or 'n/a'}"

    def __repr__(self):
        return str(self)

    @property
    def base(self):
        base = self.data.get("base")
        if base is None:
            return
        return Ref(repo=self.repo, name=base["ref"])

    @property
    def head(self):
        head = self.data.get("head")
        if head is None:
            return
        return Ref(repo=self.repo, name=head["ref"])

    @property
    def title(self):
        return self.data.get("title")

    @property
    def state(self):
        return self.data.get("state")

    def load(self):
        if self.pull_number is None:
            raise ValueError("Unable to load pull request when pull number not set.")
        self.data = self.get()
        self.pull_number = self.data.get("number")

    def get(self):
        if self.pull_number is None:
            raise ValueError("Unable to load pull request when pull number not set.")

        resp = client.get(
            f"/repos/{self.repo.owner}/{self.repo.name}/pulls/{self.pull_number}"
        )
        resp.raise_for_status()
        return resp.json()

    def list(
        self,
        state: str = None,  # ["open", "closed", "all"]
        head: Ref = None,
        base: Ref = None,
        sort: str = None,  # ["created", "updated", "popularity", "long-running"]
        direct: str = None,  # ["asc", "desc"]
    ):
        print(
            "PULL PROPS",
            filter_props(
                {
                    "state": state,
                    "head": head,
                    "base": base,
                    "sort": sort,
                    "direct": direct,
                }
            ),
        )
        resp = client.get(
            f"/repos/{self.repo}/pulls",
            params=filter_props(
                {
                    "state": state,
                    "head": head,
                    "base": base,
                    "sort": sort,
                    "direct": direct,
                }
            ),
        )

        resp.raise_for_status()

        for pull in resp.json():
            yield PullRequest(
                repo=self.repo, pull_number=pull["number"],
            )

    def create(
        self,
        title: str,
        head: Ref,
        base: Ref = None,
        body: str = None,
        maintainer_can_modify=True,
        draft: bool = False,
        issue: int = None,
    ):
        base = base if base is not None else self.repo.primary_ref
        resp = client.post(
            f"/repos/{self.repo.owner}/{self.repo.name}/pulls",
            json=filter_props(
                {
                    "title": title,
                    "head": head.name,
                    "base": base.name,
                    "body": body,
                    "maintainer_can_modify": maintainer_can_modify,
                    "draft": draft,
                    "issue": issue,
                }
            ),
        )
        resp.raise_for_status()
        self.data = resp.json()
        self.pull_number = self.data["number"]
        return self

    def update(
        self,
        title: str = None,
        body: str = None,
        state: Union["open", "closed"] = None,
        base: Ref = None,
        maintainer_can_modify: bool = None,
    ):
        resp = client.patch(
            f"/repos/{self.repo.owner}/{self.repo.name}/pulls/{self.pull_number}",
            json=filter_props(
                {
                    "title": title,
                    "body": body,
                    "state": state,
                    "base": base.name if base is not None else None,
                    "maintainer_can_modify": maintainer_can_modify,
                }
            ),
        )
        resp.raise_for_status()
        self.data = resp.json()
        return self

    def is_merged(self):
        resp = client.get(
            f"/repos/{self.repo.owner}/{self.repo.name}/pulls/{self.pull_number}/merge",
        )
        if resp.status_code == 204:
            return True

        if resp.status_code == 404:
            return False

        resp.raise_for_status()

    def merge(
        self, commit_title: str, commit_message: str, merge_method: str = "merge"
    ):
        # TODO sha? : https://docs.github.com/en/rest/reference/pulls#merge-a-pull-request
        resp = client.put(
            f"/repos/{self.repo.owner}/{self.repo.name}/pulls/{self.pull_number}/merge",
            json={
                "commit_title": commit_title,
                "commit_message": commit_message,
                "merge_method": merge_method,
            },
        )
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 405:
            return MergeError(resp.json()["message"])
        elif resp.status_code == 422:
            return MergeConflictError(resp.json()["message"])

        resp.raise_for_status()

    def workflow_runs(self, event: str = None, status: str = None):
        return WorkflowRun(self.repo, branch=self.head, event="pull_request").list()

    @property
    def commits(self):
        """Get raw commit objects for pull request"""
        resp = client.get(
            f"/repos/{self.repo.owner}/{self.repo.name}/pulls/{self.pull_number}/commits",
            params={"limit": 100},
        )
        resp.raise_for_status()
        for commit in resp.json():
            yield commit


class WorkflowRun:
    def __init__(
        self,
        repo: Repo,
        run_id: str = None,
        branch: Ref = None,
        event: str = None,
        data: dict = None,
    ):
        self.repo = repo
        self.run_id = run_id
        self.branch = branch
        self.event = event
        self.data = data or {}
        if not self.data and self.run_id is not None:
            self.load()

    def __str__(self):
        return f"Workflow<{self.run_id}, {self.status}, {self.conclusion}> in {self.branch or self.repo}"

    def __repr__(self):
        return str(self)

    @property
    def name(self):
        return self.data.get("name")

    @property
    def head_branch(self):
        head = self.data.get("head_branch")
        if head is None:
            return
        return Ref(repo=self.repo, name=head)

    @property
    def status(self):
        return self.data.get("status", None)

    @property
    def conclusion(self):
        return self.data.get("conclusion", None)

    @property
    def created_at(self):
        created_at = self.data.get("created_at")
        if created_at is None:
            return
        return parser.isoparse(created_at)

    def load(self):
        self.data = self.get()
        self.run_id = self.data["id"]

    def get(self):
        resp = client.get(f"/repos/{self.repo}/actions/runs/{self.run_id}")
        resp.raise_for_status()
        return resp.json()

    def cancel(self):
        resp = client.post(f"/repos/{self.repo}/actions/runs/{self.run_id}/cancel")
        resp.raise_for_status()

    def list(
        self, branch: Ref = None, event: str = None, status: str = None
    ) -> List["WorkflowRun"]:
        branch = branch or self.branch
        event = event or self.event
        print("getting actions for ", branch)
        resp = client.get(
            f"/repos/{self.repo.owner}/{self.repo.name}/actions/runs",
            params=filter_props(
                {
                    "branch": branch.name if branch is not None else branch,
                    "event": event,
                    "status": status,
                }
            ),
        )
        resp.raise_for_status()

        for run in resp.json()["workflow_runs"]:
            yield WorkflowRun(
                repo=self.repo,
                run_id=run["id"],
                branch=Ref(
                    self.repo, name=run["head_branch"], head_sha=run["head_sha"]
                ),
                data=run,
            )

    def jobs(self, filter_: Union["latest", "all"] = "all"):
        return WorkflowJob(self.repo, self).list(filter_=filter_)


class Step:
    def __init__(self, name, status, conclusion, number, started_at, completed_at):
        self.name = name
        self.status = status
        self.conclusion = conclusion
        self.number = number
        self.started_at = (
            datetime.fromisoformat(started_at) if started_at is not None else None
        )
        self.completed_at = (
            datetime.fromisoformat(completed_at) if completed_at is not None else None
        )

    def __str__(self):
        return f"Step<name={self.name}, status={self.status}, conclusion={self.conclusion}, number={self.number}>"

    def __repr__(self):
        return str(self)


class WorkflowJob:
    def __init__(
        self, repo: Repo, workflow_run: WorkflowRun, job_id: str = None, data=None
    ):
        self.repo = repo
        self.workflow_run = workflow_run
        self.job_id = job_id
        self.data = data or {}
        if not self.data and self.job_id:
            self.load()

    def __str__(self):
        return f"{self.workflow_run} (job={self.job_id})"

    def __repr__(self):
        return str(self)

    @property
    def steps(self):
        for step in self.data["steps"]:
            yield Step(**step)

    def load(self):
        self.data = self.get()

    def get(self):
        resp = client.get(
            f"/repos/{self.repo}/actions/runs/{self.workflow_run.run_id}/jobs/{self.job_id}"
        )
        resp.raise_for_status()
        return resp.json()

    def logs(self):
        resp = client.get(f"/repos/{self.repo}/actions/jobs/{self.job_id}/logs")
        if resp.status_code == 404:
            raise FileNotFoundError
        resp.raise_for_status()
        return resp.text

    def list(self, filter_: Union["latest", "all"] = "all"):
        resp = client.get(
            f"/repos/{self.repo}/actions/runs/{self.workflow_run.run_id}/jobs",
            params=filter_props({"filter": filter_}),
        )
        resp.raise_for_status()
        for wfj in resp.json()["jobs"]:
            yield WorkflowJob(
                repo=self.repo,
                workflow_run=self.workflow_run,
                job_id=wfj["id"],
                data=wfj,
            )


class Tree:
    def __init__(
        self,
        repo: Repo,
        path: str = None,
        ref: Ref = None,
        data: dict = None,
        base_tree: "Tree" = None,
        load_data=True,
    ):
        self.repo = repo
        self.path = path
        self.ref = ref
        self.data = data or {}
        self.sub_trees = None
        self.base_tree = base_tree
        if load_data and not self.data:
            self.load()

    @property
    def sha(self):
        return self.data["sha"]

    @property
    def type_(self):
        return self.data.get("type", "tree")

    @property
    def url(self):
        return self.data["url"]

    def load(self):
        if self.ref is None and self.data is None:
            raise ValueError("Ref and sha not specified.")

        sha = self.data["sha"] if self.data else self.ref.sha

        owner, name = self.repo.owner, self.repo.name
        resp = client.get(f"/repos/{owner}/{name}/git/trees/{sha}",)
        resp.raise_for_status()

        self.data = resp.json()

        return self.data

    def __iter__(self):
        if self.data is None:
            self.load()

        for tree_obj in self.data["tree"]:
            if tree_obj["type"] == "tree":
                sub_tree = Tree(
                    repo=self.repo,
                    path=tree_obj["path"],
                    ref=self.ref,
                    data=tree_obj,
                    base_tree=self,
                )
                if sub_tree.ref is not None:
                    sub_tree.load()
                yield sub_tree
            elif tree_obj["type"] == "blob":
                yield Blob(
                    repo=self.repo, ref=self.ref, tree=self, data=tree_obj,
                )

    def create(self, tree: List[dict]):
        owner, name = self.repo.owner, self.repo.name
        resp = client.post(
            f"/repos/{owner}/{name}/git/trees",
            json={"base_tree": self.sha, "tree": tree},
        )
        resp.raise_for_status()
        return Tree(
            repo=self.repo, path=None, ref=self.ref, data=resp.json(), base_tree=self,
        )


class Blob:
    def __init__(
        self,
        repo: Repo,
        ref: Ref = None,
        tree: Tree = None,
        data: dict = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.repo = repo
        self.ref = ref
        self.tree = tree
        self.data = data

    @property
    def sha(self):
        return self.data["sha"]

    @property
    def path(self):
        return self.data["path"]

    @property
    def mode(self):
        return self.data["mode"]

    @property
    def type_(self):
        return self.data["type"]

    @property
    def size(self):
        return self.data["size"]

    def load(self):
        resp = client.get(
            f"/repos/{self.repo.owner}/{self.repo.name}/git/blobs/{self.sha}"
        )
        resp.raise_for_status()
        self.data = resp.json()
        return self.data


class Commit:
    def __init__(
        self, repo: Repo, message: str, tree: Tree, parents: List[Union[Ref, Tree]],
    ):
        self.repo = repo
        self.message = message
        self.tree = tree
        self.parents = parents
        self.data = None

        self.create()

    def create(self):
        resp = client.post(
            f"/repos/{self.repo.owner}/{self.repo.name}/git/commits",
            json={
                "tree": self.tree.sha,
                "message": self.message,
                "parents": [parent.sha for parent in self.parents],
            },
        )
        print(resp.text)
        resp.raise_for_status()
        self.data = resp.json()
        return self.data


class GitHub:
    def __init__(self, api_token=None):
        global client
        client = get_client(api_token)

    def repo(self, owner, name, primary_branch="main"):
        return Repo(owner, name, primary_branch=primary_branch)

    def ref(self, repo: Repo, name: str, load_data: bool = True):
        return Ref(repo, name, load_data=True)

    def content(self, repo: Repo, path: str, ref: Ref = None):
        return Content(repo, path, ref=ref)

    def pull_request(self, repo: Repo, pull_number: int = None):
        return PullRequest(repo, pull_number=pull_number)
