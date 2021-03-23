import uuid

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    DateTime,
    JSON,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.schema import UniqueConstraint

from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    url = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)

    hashed_password = Column(String, nullable=False)

    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
    is_approved = Column(Boolean(), default=False)

    client_id = Column(String)
    client_secret = Column(String)
    access_token = Column(String)
    access_token_expires_at = Column(DateTime)

    jobs = relationship("Job", back_populates="user")
    projects = relationship("Project", back_populates="user")


class Job(Base):
    __tablename__ = "jobs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    created_at = Column(DateTime)
    finished_at = Column(DateTime)
    status = Column(String)
    inputs = Column(JSON)
    outputs = Column(JSON)
    tag = Column(String)

    user = relationship("User", back_populates="jobs")


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    tech = Column(String, nullable=False)
    callable_name = Column(String)
    exp_task_time = Column(String, nullable=False)
    cpu = Column(Float)
    memory = Column(Float)

    user = relationship("User", back_populates="projects")

    __table_args__ = (
        UniqueConstraint(
            "owner", "title", "user_id", name="unique_owner_title_project",
        ),
    )

    class Config:
        orm_mode = True
        extra = "ignore"
