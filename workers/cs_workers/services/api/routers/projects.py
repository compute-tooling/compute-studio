from typing import List

from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session

from .. import models, schemas, dependencies as deps, settings

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/sync/", response_model=List[schemas.Project], status_code=200)
def sync_projects(
    projects: List[schemas.ProjectSync] = Body(...),
    db: Session = Depends(deps.get_db),
    user: schemas.User = Depends(deps.get_current_active_user),
):
    orm_projects = []
    for project in projects:
        orm_project = (
            db.query(models.Project)
            .filter(
                models.Project.title == project.title,
                models.Project.owner == project.owner,
                models.Project.user_id == user.id,
            )
            .one_or_none()
        )
        project_data = project.dict()
        if orm_project is None:
            print("creating object from data", project_data)
            orm_project = models.Project(**project_data, user_id=user.id)
        else:
            print("updating object from data", project_data)
            for attr, val in project.dict().items():
                print("setting", attr, val)
                setattr(orm_project, attr, val)
        orm_projects.append(orm_project)
    db.add_all(orm_projects)
    db.commit()
    return orm_projects


@router.get("/", response_model=schemas.PaginatedProject, status_code=200)
def get_projects(
    db: Session = Depends(deps.get_db),
    user: schemas.UserInDB = Depends(deps.get_current_active_user),
    page: int = 0,
):
    if user.is_superuser:
        user_projects = db.query(models.Project)
    else:
        user_projects = db.query(models.Project).filter(
            models.Project.user_id == user.id
        )

    results = user_projects.limit(30).offset(page)
    total_count = results.count()

    if settings.settings.WORKERS_API_HOST:
        url = f"https://{settings.settings.WORKERS_API_HOST}"
    else:
        url = f"http://api.{settings.settings.NAMESPACE}.svc.cluster.local"

    url += settings.settings.API_PREFIX_STR

    if total_count == 30:
        next_page = f"{url}?page={page+1}"
    else:
        next_page = None

    if page > 0:
        previous_page = f"{url}?page={page-1}"
    else:
        previous_page = None

    return {
        "count": total_count,
        "next": next_page,
        "previous": previous_page,
        "results": results.all(),
    }
