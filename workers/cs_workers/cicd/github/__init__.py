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


def create_job(owner, title, primary_branch="production", build_id=None):
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

    if build_id is not None:
        build_id_msg = f" build_id={build_id}"
    else:
        build_id_msg = ""

    message = f"(auto) Update {owner}/{title} - {str(now.strftime('%Y-%m-%d %H:%M'))}{build_id_msg}"

    gh.content(repo=repo, path=f"config/{owner}/{title}.yaml", ref=ref).write(
        yaml.dump(
            {
                "owner": owner,
                "title": title,
                "timestamp": str(now.strftime("%Y-%m-%d %H:%M")),
                "build_id": build_id,
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
    primary_branch="production",
    **kwargs,
):
    if isinstance(pull_request, int):
        gh = GitHub(token)
        repo = gh.repo(repo_owner, repo_name, primary_branch=primary_branch)
        pull_request = PullRequest(repo, pull_request)
    workflow_runs = list(pull_request.workflow_runs())
    if not workflow_runs:
        return
    wf_runs_list = list(workflow_runs)
    pr_commits_list = list(pull_request.commits)

    if len(wf_runs_list) != len(pr_commits_list):
        return {
            "stage": "created",
            "failed_at_stage": None,
            "workflow_run": None,
            "workflow_job": None,
            "logs": [],
            "pull_request": pull_request,
        }
    wf = max(workflow_runs, key=attrgetter("created_at"))
    job = next(wf.jobs())

    stage = "created"
    failed_at_stage = None

    step_map = {"Build": "building", "Test": "testing", "Push": "staging"}
    for step in job.steps:
        print("checking step", step.name, step.status, step.conclusion)
        if step.name not in step_map:
            continue

        if step.status == "in_progress":
            stage = step_map[step.name]
            break
        elif step.conclusion == "failure":
            stage = "failure"
            failed_at_stage = step_map[step.name]
            break

    # likely redundant
    if wf.conclusion:
        stage = wf.conclusion

    try:
        logs = parse_logs(job.logs())
    except FileNotFoundError:
        logs = None
    return {
        "stage": stage,
        "failed_at_stage": failed_at_stage,
        "workflow_run": wf,
        "workflow_job": job,
        "logs": logs,
        "pull_request": pull_request,
    }


class JobFailedException(Exception):
    pass


class JobNotReadyException(Exception):
    pass


def deploy(
    repo_owner: str,
    repo_name: str,
    pull_request: Union[int, PullRequest],
    primary_branch="production",
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

    if wf.conclusion == "failure":
        raise JobFailedException()
    elif wf.conclusion != "success":
        raise JobNotReadyException()

    pull_request.merge(
        commit_title=f"Update {repo_owner}/{repo_name} (#{pull_request.pull_number})",
        commit_message="",
    )


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
