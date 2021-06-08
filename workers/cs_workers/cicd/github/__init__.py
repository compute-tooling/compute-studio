from datetime import datetime
from operator import attrgetter
import os
import random
import yaml
from .api import GitHub, PullRequest, Repo
from .logs import parse_logs

token = os.environ.get("GITHUB_TOKEN")


def existing_app_pr(owner, title, repo: Repo):
    pull = None
    ref = None
    for pull in repo.pull_requests(state="open"):
        if f"{owner}/{title}" in pull.title:
            print(f"Found open pull request for app: {pull}")
            pull = pull
            ref = pull.head

    return pull, ref


def create_job(owner, title):
    gh = GitHub(token)
    repo = gh.repo("compute-tooling", "compute-studio-publish", primary_branch="master")

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

    if pull is None:
        return gh.pull_request(repo).create(title=message, head=ref)
    else:
        return pull


def job_status(pull: PullRequest):
    workflow_runs = list(pull.workflow_runs())
    if not workflow_runs:
        return
    wf = max(workflow_runs, key=attrgetter("created_at"))
    job = next(wf.jobs())

    stage = "staging"
    for step in job.steps:
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
    }
