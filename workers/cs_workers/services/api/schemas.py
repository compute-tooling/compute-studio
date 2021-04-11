from datetime import datetime
from typing import List, Optional, Dict, Optional, Any
from enum import Enum
import uuid

from pydantic import BaseModel, Json  # pylint: disable=no-name-in-module
from pydantic.networks import EmailStr, AnyHttpUrl  # pylint: disable=no-name-in-module


class JobBase(BaseModel):
    user_id: int
    created_at: datetime
    name: str
    created_at: datetime
    finished_at: Optional[datetime]
    status: str
    inputs: Optional[Dict]
    outputs: Optional[Dict]
    traceback: Optional[str]
    tag: str


class JobCreate(JobBase):
    pass


class Job(JobBase):
    id: uuid.UUID

    class Config:
        orm_mode = True


class TaskComplete(BaseModel):
    model_version: Optional[str]
    outputs: Optional[Dict]
    traceback: Optional[str]
    version: Optional[str]
    meta: Dict  # Dict[str, str]
    status: str
    task_name: str


class Task(BaseModel):
    task_id: Optional[str]
    task_name: str
    task_kwargs: Dict  # Dict[str, str]
    tag: str


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


class CSOauthResponse(BaseModel):
    access_token: str
    expires_in: int
    token_type: str
    scope: str


class ProjectSync(BaseModel):
    owner: str
    title: str
    tech: str
    callable_name: Optional[str]
    exp_task_time: int
    cpu: float
    memory: float


class Project(ProjectSync):
    id: int

    class Config:
        orm_mode = True
        extra = "ignore"


class DeploymentCreate(BaseModel):
    tag: str
    deployment_name: str


class ReadyStats(BaseModel):
    created_at: datetime
    ready: bool


class DeploymentReadyStats(BaseModel):
    deployment: ReadyStats
    svc: ReadyStats
    ingressroute: ReadyStats


class Deleted(BaseModel):
    deleted: bool


class DeploymentDelete(BaseModel):
    deployment: Deleted
    svc: Deleted
    ingressroute: Deleted
