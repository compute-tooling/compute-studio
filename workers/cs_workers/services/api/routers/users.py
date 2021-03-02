from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic.networks import EmailStr, AnyHttpUrl  # pylint: disable=no-name-in-module

from .. import schemas, models, dependencies as deps, security

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=schemas.User)
def read_user_me(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user


@router.post("/", response_model=schemas.User, status_code=201)
def create_user(
    *,
    db: Session = Depends(deps.get_db),
    password: str = Body(...),
    email: EmailStr = Body(...),
    url: AnyHttpUrl = Body(...),
    username: str = Body(None),
) -> models.User:
    """
    Create new user.
    """
    user = db.query(models.User).filter(models.User.username == username).one_or_none()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system",
        )
    user_in = schemas.UserCreate(
        password=password, email=email, username=username, url=url
    )
    user_db = models.User(
        email=user_in.email,
        username=user_in.username,
        url=user_in.url,
        hashed_password=security.get_password_hash(user_in.password),
    )
    db.add(user_db)
    db.commit()
    db.refresh(user_db)
    return user_db


@router.post("/approve/", response_model=schemas.User)
def approve_user(
    *,
    db: Session = Depends(deps.get_db),
    current_super_user: models.User = Depends(deps.get_current_active_superuser),
    user_approve: schemas.UserApprove = Body(...),
) -> models.User:
    """
    Create new user.
    """
    user: models.User = db.query(models.User).filter(
        models.User.username == user_approve.username
    ).one_or_none()
    if not user:
        raise HTTPException(
            status_code=400, detail="The user with this username does not exist",
        )
    user.is_approved = user_approve.is_approved
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
