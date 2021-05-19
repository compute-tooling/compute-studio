from datetime import datetime
import os

import httpx
from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session

from cs_workers.models.clients import job
from .. import utils, models, schemas, dependencies as deps, security, settings

incluster = os.environ.get("KUBERNETES_SERVICE_HOST", False) is not False

PROJECT = os.environ.get("PROJECT")


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/callback/{job_id}/", status_code=201, response_model=schemas.Job)
def job_callback(
    job_id: str, db: Session = Depends(deps.get_db),
):
    instance: models.Job = db.query(models.Job).filter(
        models.Job.id == job_id
    ).one_or_none()
    if instance is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    print(instance.finished_at)
    if instance.finished_at:
        raise HTTPException(
            status_code=403, detail="No permission to retrieve job once it's finished."
        )

    if instance.status == "CREATED":
        instance.status = "RUNNING"
        db.add(instance)
        db.commit()
        db.refresh(instance)

    print(instance.inputs)

    return instance


@router.post("/callback/{job_id}/", status_code=201, response_model=schemas.Job)
async def finish_job(
    job_id: str,
    task: schemas.TaskComplete = Body(...),
    db: Session = Depends(deps.get_db),
):
    print("got data for ", job_id)
    instance = db.query(models.Job).filter(models.Job.id == job_id).one_or_none()
    if instance is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    if instance.finished_at:
        raise HTTPException(status_code=400, detail="Job already marked as complete.")

    instance.outputs = task.outputs
    instance.status = task.status
    instance.finished_at = datetime.utcnow()

    db.add(instance)
    db.commit()
    db.refresh(instance)

    user = instance.user
    await security.ensure_cs_access_token(db, user)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"http://outputs-processor/{job_id}/",
            json={
                "url": user.url,
                "headers": {"Authorization": f"Bearer {user.access_token}"},
                "task": task.dict(),
            },
        )
        print(resp.text)
        resp.raise_for_status()

    return instance


@router.post("/{owner}/{title}/", response_model=schemas.Job, status_code=201)
def create_job(
    owner: str,
    title: str,
    task: schemas.Task = Body(...),
    db: Session = Depends(deps.get_db),
    user: schemas.User = Depends(deps.get_current_active_user),
):
    print(owner, title)
    print(task.task_kwargs)
    project = (
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

    task_name, _, task_kwargs, tag = (
        task.task_name,
        task.task_id,
        task.task_kwargs,
        task.tag,
    )

    instance = models.Job(
        user_id=user.id,
        name=task_name,
        created_at=datetime.utcnow(),
        finished_at=None,
        inputs=task_kwargs,
        tag=tag,
        status="CREATED",
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)

    project_data = schemas.Project.from_orm(project).dict()

    # Use lower memory target for these tasks.
    if task_name in ("version", "defaults", "parse",):
        project_data["resources"] = {
            "requests": {"memory": f"0.25G", "cpu": 0.7},
            "limits": {"memory": f"0.7G", "cpu": 1},
        }
    else:
        utils.set_resource_requirements(project_data)

    if settings.settings.WORKERS_API_HOST:
        url = f"https://{settings.settings.WORKERS_API_HOST}"
    else:
        url = f"http://api.{settings.settings.NAMESPACE}.svc.cluster.local"

    url += settings.settings.API_PREFIX_STR

    client = job.Job(
        PROJECT,
        owner,
        title,
        tag=tag,
        model_config=project_data,
        job_id=instance.id,
        callback_url=f"{url}/jobs/callback/{instance.id}/",
        route_name=task_name,
        incluster=incluster,
        namespace=settings.settings.PROJECT_NAMESPACE,
    )

    client.create()

    return instance
