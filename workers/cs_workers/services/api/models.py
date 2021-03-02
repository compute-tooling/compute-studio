from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
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

    jobs = relationship("Job", back_populates="owner")
    projects = relationship("Project", back_populates="user")


class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime)

    owner = relationship("User", back_populates="jobs")


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    tech = Column(String, nullable=False)
    callable_name = Column(String)
    exp_task_time = Column(String, nullable=False)
    cpu = Column(Integer)
    memory = Column(Integer)

    user = relationship("User", back_populates="projects")

    __table_args__ = (
        UniqueConstraint(
            "owner", "title", "user_id", name="unique_owner_title_project",
        ),
    )

    class Config:
        orm_mode = True
        extra = "ignore"
