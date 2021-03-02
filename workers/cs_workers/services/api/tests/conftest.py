from typing import Dict, Generator

import pytest
from fastapi.testclient import TestClient

import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker, exc

from ..settings import settings
from ..database import SessionLocal
from ..main import app
from ..dependencies import get_db
from .. import models, schemas, security


SQLALCHEMY_DATABASE_URI = f"postgresql://{settings.DB_USER}:{settings.TEST_DB_PASS}@{settings.DB_HOST}/{settings.TEST_DB_NAME}"
assert settings.DB_NAME != settings.TEST_DB_NAME

engine = create_engine(SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)

Base = declarative_base()

Base.metadata.create_all(bind=engine)


# Adapted from:
# https://github.com/jeancochrane/pytest-flask-sqlalchemy/blob/c109469f83450b8c5ff5de962faa1105064f5619/pytest_flask_sqlalchemy/fixtures.py#L25-L84
@pytest.fixture(scope="function")
def db(request) -> Generator:
    connection = engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=connection
    )
    session = TestingSessionLocal()

    # Make sure the session, connection, and transaction can't be closed by accident in
    # the codebase
    connection.force_close = connection.close
    transaction.force_rollback = transaction.rollback

    connection.close = lambda: None
    transaction.rollback = lambda: None
    session.close = lambda: None

    session.begin_nested()
    # Each time the SAVEPOINT for the nested transaction ends, reopen it
    @sa.event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, trans):
        if trans.nested and not trans._parent.nested:
            # ensure that state is expired the way
            # session.commit() at the top level normally does
            session.expire_all()

            session.begin_nested()

    # Force the connection to use nested transactions
    connection.begin = connection.begin_nested

    # If an object gets moved to the 'detached' state by a call to flush the session,
    # add it back into the session (this allows us to see changes made to objects
    # in the context of a test, even when the change was made elsewhere in
    # the codebase)
    @sa.event.listens_for(session, "persistent_to_detached")
    @sa.event.listens_for(session, "deleted_to_detached")
    def rehydrate_object(session, obj):
        session.add(obj)

    @request.addfinalizer
    def teardown_transaction():
        # Delete the session
        session.close()

        # Rollback the transaction and return the connection to the pool
        transaction.force_rollback()
        connection.force_close()

    app.dependency_overrides[get_db] = lambda: session
    return session


@pytest.fixture(scope="function")
def client() -> Generator:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def new_user(db):
    user_ = models.User(
        username="test",
        email="test@test.com",
        url="http://localhost:8000",
        hashed_password=security.get_password_hash("heyhey2222"),
    )
    db.add(user_)
    db.commit()
    db.refresh(user_)
    return user_


@pytest.fixture(scope="function")
def user(db, new_user):
    new_user.approved = True
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@pytest.fixture(scope="function")
def superuser(db):
    user_ = models.User(
        username="super-user",
        email="super-user@test.com",
        url="http://localhost:8000",
        hashed_password=security.get_password_hash("heyhey2222"),
        is_superuser=True,
    )
    db.add(user_)
    db.commit()
    db.refresh(user_)
    yield user_
