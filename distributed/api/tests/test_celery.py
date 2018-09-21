import pytest
from celery import chord

from api.celery_tasks import ()

@pytest.fixture(scope='session')
def celery_config():
    return {
        'broker_url': 'redis://localhost:6379',
        'result_backend': 'redis://localhost:6379',
        'task_serializer': 'json',
        'accept_content': ['msgpack', 'json']}
