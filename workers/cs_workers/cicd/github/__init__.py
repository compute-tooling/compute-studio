from datetime import datetime
from operator import attrgetter
import os
import random
from typing import Union
import yaml
from .api import GitHub, PullRequest, Repo
from .logs import parse_logs

token = os.environ.get("GITHUB_TOKEN")


def existing_app_pr(owner, title, repo: Repo):
    pull = None
    ref = None
    for open_pull in repo.pull_requests(state="open"):
        if f"{owner}/{title}" in open_pull.title:
            print(f"Found open pull request for app: {open_pull}")
            pull = open_pull
            ref = open_pull.head

    return pull, ref


def create_job(owner, title, primary_branch="hdoupe-local"):
    gh = GitHub(token)
    repo = gh.repo(
        "compute-tooling", "compute-studio-publish", primary_branch=primary_branch
    )

    pull, ref = existing_app_pr(owner, title, repo)
    now = datetime.now()

    if ref is None:
        ref_name = (
            "update-"
            + str(now.strftime("%Y-%m-%d"))
            + "-"
            + str(random.randint(1111, 9999))
        )
        ref = repo.create_ref(ref_name)
        print(f"Created new ref: {ref}")

    message = f"(auto) Update {owner}/{title} - {str(now.strftime('%Y-%m-%d %H:%M'))}"

    gh.content(repo=repo, path=f"config/{owner}/{title}.yaml", ref=ref).write(
        yaml.dump(
            {
                "owner": owner,
                "title": title,
                "timestamp": str(now.strftime("%Y-%m-%d %H:%M")),
            }
        ),
        message=message,
    )
    print("got pull", pull)
    if pull is None:
        return gh.pull_request(repo).create(title=message, head=ref)
    else:
        return pull


def job_status(
    repo_owner: str,
    repo_name: str,
    pull_request: Union[int, PullRequest],
    primary_branch="hdoupe-local",
    **kwargs,
):
    if isinstance(pull_request, int):
        gh = GitHub(token)
        repo = gh.repo(repo_owner, repo_name, primary_branch=primary_branch)
        pull_request = PullRequest(repo, pull_request)
    workflow_runs = list(pull_request.workflow_runs())
    if not workflow_runs:
        return
    wf = max(workflow_runs, key=attrgetter("created_at"))
    job = next(wf.jobs())

    if wf.conclusion in ("success", "failure"):
        stage = wf.conclusion

    else:
        stage = "staging"
        for step in job.steps:
            print("checking step", step.name)
            if step.started_at and not step.completed_at:
                if step.name == "Build":
                    stage = "building"
                elif step.name == "Test":
                    stage = "testing"
                elif step.name == "Push":
                    stage = "pushing"
                break

    try:
        logs = parse_logs(job.logs())
    except FileNotFoundError:
        logs = None
    return {
        "stage": stage,
        "workflow_run": wf,
        "workflow_job": job,
        "logs": logs,
        "pull_request": pull_request,
    }


def cancel_job(
    repo_name: str, repo_title: str, pull_request: Union[int, PullRequest], **kwargs
):
    if isinstance(pull_request, int):
        gh = GitHub(token)
        repo = gh.repo(repo_name, repo_title)
        pull_request = PullRequest(repo, pull_request)
    workflow_runs = list(pull_request.workflow_runs())
    if not workflow_runs:
        return
    wf = max(workflow_runs, key=attrgetter("created_at"))
    wf.cancel()
