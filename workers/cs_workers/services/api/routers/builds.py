from datetime import date, datetime
import os

from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session

from cs_workers.cicd import github as github_actions
from .. import utils, models, schemas, dependencies as deps, settings

incluster = os.environ.get("KUBERNETES_SERVICE_HOST", False) is not False

PROJECT = os.environ.get("PROJECT")


router = APIRouter(prefix="/builds", tags=["builds"])


@router.post("/{owner}/{title}/", response_model=schemas.Build, status_code=201)
def create(
    owner: str,
    title: str,
    db: Session = Depends(deps.get_db),
    user: schemas.User = Depends(deps.get_current_active_user),
):
    print("create new build")
    project: models.Project = (
        db.query(models.Project)
        .filter(
            models.Project.owner == owner,
            models.Project.title == title,
            models.Project.user_id == user.id,
        )
        .one_or_none()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    pull_request = github_actions.create_job(project.owner, project.title)

    build = models.Build(
        project_id=project.id,
        created_at=datetime.utcnow(),
        provider="github",
        provider_data={
            "repo_owner": pull_request.repo.owner,
            "repo_name": pull_request.repo.name,
            "pull_request": pull_request.pull_number,
        },
        status="created",
    )

    return build


@router.get("/{build_id}/", response_model=schemas.Build, status_code=201)
def get(
    build_id: str,
    db: Session = Depends(deps.get_db),
    user: schemas.User = Depends(deps.get_current_active_user),
):
    print("check build status")
    build: models.Build = (
        db.query(models.Build)
        .join(models.Project)
        .filter(models.Project.user_id == user.id, models.Build.id == build_id,)
        .one_or_none()
    )

    if not build:
        raise HTTPException(status_code=404, detail="Build not found.")

    build_data = schemas.Build.from_orm(build).todict()

    status = github_actions.job_status(**build_data["provider_data"])

    build.provider_data["stage"] = status["stage"]
    build.status = status["stage"]
    db.add(build)
    db.commit()
    db.refresh(build)

    build_data = schemas.Build.from_orm(build)
    build_data.provider_data.logs = status["logs"]

    return build_data


@router.delete("/{build_id}/", response_model=schemas.Build, status_code=201)
def delete(
    build_id: str,
    db: Session = Depends(deps.get_db),
    user: schemas.User = Depends(deps.get_current_active_user),
):
    print("cancel build")
    build: models.Build = (
        db.query(models.Build)
        .join(models.Project)
        .filter(models.Project.user_id == user.id, models.Build.id == build_id,)
        .one_or_none()
    )

    if not build:
        raise HTTPException(status_code=404, detail="Build not found.")

    build_data = schemas.Build.from_orm(build).todict()

    github_actions.cancel_job(**build_data["provider_data"])

    build.provider_data["stage"] = "cancelled"
    build.status = "cancelled"
    build.cancelled_at = datetime.utcnow()
    db.add(build)
    db.commit()
    db.refresh(build)

    build_data = schemas.Build.from_orm(build)

    return build_data
