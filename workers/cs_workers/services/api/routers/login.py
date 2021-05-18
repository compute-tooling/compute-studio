from datetime import timedelta, datetime
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

import pytz
from sqlalchemy.orm import Session

from .. import security
from ..models import User
from .. import schemas
from .. import dependencies as deps
from ..settings import settings

router = APIRouter(tags=["login"])


def authenticate(db: Session, *, username: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.username == username).one_or_none()
    if not user:
        return None
    if not security.verify_password(password, user.hashed_password):
        return None
    return user


@router.post("/login/access-token", response_model=schemas.Token)
def login_access_token(
    db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = authenticate(db, username=form_data.username, password=form_data.password)

    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
        "expires_at": datetime.now().replace(tzinfo=pytz.UTC) + access_token_expires,
    }
