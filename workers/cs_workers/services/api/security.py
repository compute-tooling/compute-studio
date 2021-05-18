from datetime import datetime, timedelta
from typing import Any, Union

import httpx
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from fastapi import HTTPException

from .settings import settings
from . import schemas
from . import models

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


ALGORITHM = "HS256"


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.API_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


async def ensure_cs_access_token(db: Session, user: models.User):
    missing_token = user.access_token is None
    is_expired = (
        user.access_token_expires_at is not None
        and user.access_token_expires_at < (datetime.utcnow() - timedelta(seconds=60))
    )
    if missing_token or is_expired:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{user.url}/o/token/",
                data={
                    "grant_type": "client_credentials",
                    "client_id": user.client_id,
                    "client_secret": user.client_secret,
                },
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail=resp.text)
            data = schemas.CSOauthResponse(**resp.json())
            user.access_token = data.access_token
            user.access_token_expires_at = datetime.utcnow() + timedelta(
                seconds=data.expires_in
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    return user
