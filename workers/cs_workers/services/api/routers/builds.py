from datetime import date, datetime
import os

from fastapi import APIRouter, Depends, Body, HTTPException
import httpx
from sqlalchemy.orm import Session

from cs_workers.cicd import github as github_actions
from fastapi.responses import JSONResponse
from sqlalchemy.sql.functions import user
from .. import models, schemas, dependencies as deps, security

incluster = os.environ.get("KUBERNETES_SERVICE_HOST", False) is not False

PROJECT = os.environ.get("PROJECT")


router = APIRouter(prefix="/builds", tags=["builds"])


@router.post("/{build_id}/done/", response_model=schemas.Build, status_code=200)
async def build_done(
    build_id: int,
    db: Session = Depends(deps.get_db),
    # TODO: use scoped build user instead of super user
    # https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/?h=security#use-securityscopes
    current_super_user: models.User = Depends(deps.get_current_active_superuser),
    artifact: schemas.BuildArtifact = Body(...),
):
    print("check build status", build_id, artifact.dict())
    build: models.Build = (
        db.query(models.Build)
        .join(models.Project)
        .join(models.User)
        .filter(models.Build.id == build_id,)
        .one_or_none()
    )

    if not build:
        raise HTTPException(status_code=404, detail="Build not found.")

    build_data = schemas.Build.from_orm(build).dict()
    status = github_actions.job_status(**build_data["provider_data"])
    if status:
        build.provider_data = {
            "stage": status["stage"],
            "repo_owner": status["pull_request"].repo.owner,
            "repo_name": status["pull_request"].repo.name,
            "pull_request": status["pull_request"].pull_number,
        }
        build.status = status["stage"]
        build.failed_at_stage = status["failed_at_stage"]

    build.finished_at = datetime.utcnow()
    build.image_tag = artifact.image_tag
    build.version = artifact.version
    db.add(build)
    db.commit()
    db.refresh(build)

    refreshed_data = schemas.Build.from_orm(build).dict()

    if status:
        refreshed_data["provider_data"]["logs"] = status["logs"]

    # TODO: post back to cs webapp
    await security.ensure_cs_access_token(db, build.project.user)

    data = {
        "tag": {"image_tag": build.image_tag, "version": build.version},
        "project": f"{build.project.owner}/{build.project.title}",
        "cluster_build_id": build.id,
    }
    for field in [
        "created_at",
        "finished_at",
        "cancelled_at",
        "status",
        "provider_data",
        "failed_at_stage",
    ]:
        data[field] = refreshed_data.get(field, None)

    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{build.project.user.url}/projects/api/v1/builds/{build.id}/?cluster_id=true",
            data=schemas.WebappBuildCallback(**data).json(),
            headers={
                "Authorization": f"Bearer {build.project.user.access_token}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()

    return refreshed_data


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

    build = models.Build(
        project_id=project.id,
        created_at=datetime.utcnow(),
        provider="github",
        status="created",
    )
    db.add(build)
    db.commit()
    db.refresh(build)

    pull_request = github_actions.create_job(
        project.owner, project.title, build_id=build.id
    )

    build.created_at = datetime.utcnow()
    build.provider = "github"
    build.provider_data = {
        "stage": "started",
        "repo_owner": pull_request.repo.owner,
        "repo_name": pull_request.repo.name,
        "pull_request": pull_request.pull_number,
    }
    db.add(build)
    db.commit()
    db.refresh(build)

    return schemas.Build.from_orm(build)


@router.get("/{build_id}/", response_model=schemas.Build, status_code=200)
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

    build_data = schemas.Build.from_orm(build).dict()

    status = github_actions.job_status(**build_data["provider_data"])
    if status:
        build.provider_data = {
            "stage": status["stage"],
            "repo_owner": status["pull_request"].repo.owner,
            "repo_name": status["pull_request"].repo.name,
            "pull_request": status["pull_request"].pull_number,
        }
        build.status = status["stage"]
        build.failed_at_stage = status["failed_at_stage"]

    if build.status in ("success", "failure") and build.finished_at is None:
        build.finished_at = datetime.utcnow()
    db.add(build)
    db.commit()
    db.refresh(build)

    build_data = schemas.Build.from_orm(build)
    print("Build status", build.status)

    if status:
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
