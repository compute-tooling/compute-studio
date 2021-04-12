import os

from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session

from cs_workers.models.clients import server
from .. import utils, models, schemas, dependencies as deps, security, settings

incluster = os.environ.get("KUBERNETES_SERVICE_HOST", False) is not False

PROJECT = os.environ.get("PROJECT")


router = APIRouter(prefix="/deployments", tags=["deployments"])


@router.post(
    "/{owner}/{title}/", response_model=schemas.DeploymentReadyStats, status_code=201
)
def create_deployment(
    owner: str,
    title: str,
    data: schemas.DeploymentCreate = Body(...),
    db: Session = Depends(deps.get_db),
    user: schemas.User = Depends(deps.get_current_active_user),
):
    print("create deployment", data)
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

    if project.tech not in ("dash", "bokeh"):
        return HTTPException(status_code=400, detail=f"Unsuported tech: {project.tech}")

    project_data = schemas.Project.from_orm(project).dict()
    utils.set_resource_requirements(project_data)

    viz = server.Server(
        project=PROJECT,
        owner=project.owner,
        title=project.title,
        tag=data.tag,
        model_config=project_data,
        callable_name=project.callable_name,
        deployment_name=data.deployment_name,
        incluster=incluster,
        viz_host=settings.settings.VIZ_HOST,
        namespace=settings.settings.PROJECT_NAMESPACE,
    )
    dep = viz.deployment_from_cluster()
    if dep is not None:
        raise HTTPException(status_code=400, detail="Deployment is already running.")

    viz.configure()
    viz.create()
    ready_stats = schemas.DeploymentReadyStats(viz.ready_stats())
    return ready_stats


@router.get(
    "/{owner}/{title}/{deployment_name}/",
    response_model=schemas.DeploymentReadyStats,
    status_code=201,
)
def get_deployment(
    owner: str,
    title: str,
    deployment_name: str,
    db: Session = Depends(deps.get_db),
    user: schemas.User = Depends(deps.get_current_active_user),
):
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

    if project.tech not in ("dash", "bokeh"):
        return HTTPException(status_code=400, detail=f"Unsuported tech: {project.tech}")

    project_data = schemas.Project.from_orm(project).dict()
    utils.set_resource_requirements(project_data)

    viz = server.Server(
        project=PROJECT,
        owner=project.owner,
        title=project.title,
        tag=None,
        model_config=project_data,
        callable_name=project.callable_name,
        deployment_name=deployment_name,
        incluster=incluster,
        viz_host=settings.settings.VIZ_HOST,
        namespace=settings.settings.PROJECT_NAMESPACE,
    )

    ready_stats = schemas.DeploymentReadyStats(viz.ready_stats())
    return ready_stats


@router.delete(
    "/{owner}/{title}/{deployment_name}/",
    response_model=schemas.DeploymentReadyStats,
    status_code=201,
)
def delete_deployment(
    owner: str,
    title: str,
    deployment_name: str,
    db: Session = Depends(deps.get_db),
    user: schemas.User = Depends(deps.get_current_active_user),
):
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

    if project.tech not in ("dash", "bokeh"):
        return HTTPException(status_code=400, detail=f"Unsuported tech: {project.tech}")

    project_data = schemas.Project.from_orm(project).dict()
    utils.set_resource_requirements(project_data)

    viz = server.Server(
        project=PROJECT,
        owner=project.owner,
        title=project.title,
        tag=None,
        model_config=project_data,
        callable_name=project.callable_name,
        deployment_name=deployment_name,
        incluster=incluster,
        viz_host=settings.settings.VIZ_HOST,
        namespace=settings.settings.PROJECT_NAMESPACE,
    )

    ready_stats = schemas.DeploymentReadyStats(viz.ready_stats())
    return ready_stats
