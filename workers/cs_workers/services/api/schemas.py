from datetime import datetime
from typing import List, Optional, Dict
from enum import Enum

from pydantic import BaseModel  # pylint: disable=no-name-in-module
from pydantic.networks import EmailStr, AnyHttpUrl  # pylint: disable=no-name-in-module


class JobBase(BaseModel):
    owner_id: int
    created_at: datetime


class JobCreate(JobBase):
    pass


class Job(JobBase):
    id: int

    class Config:
        orm_mode = True


# Shared properties
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    url: Optional[AnyHttpUrl]
    is_approved: Optional[bool]

    is_active: Optional[bool] = True


# Properties to receive via API on creation
class UserCreate(UserBase):
    email: EmailStr = None
    username: str = None
    url: AnyHttpUrl
    password: str


class UserApprove(UserBase):
    username: str
    is_approved: bool


class UserInDBBase(UserBase):
    class Config:
        orm_mode = True


# Additional properties to return via API
class User(UserInDBBase):
    pass


# Additional properties stored in DB
class UserInDB(UserInDBBase):
    id: Optional[int] = None
    hashed_password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime


class TokenPayload(BaseModel):
    sub: Optional[int] = None


class ProjectSync(BaseModel):
    owner: str
    title: str
    tech: str
    callable_name: str
    exp_task_time: int
    cpu: int
    memory: int


class Project(BaseModel):
    id: int

    class Config:
        orm_mode = True
        extra = "ignore"
