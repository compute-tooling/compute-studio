import pytest
from celery import chord

@pytest.fixture(scope='session')
def celery_config():
    return {
        'broker_url': 'redis://localhost:6379',
        'result_backend': 'redis://localhost:6379',
        'task_serializer': 'json',
        'accept_content': ['msgpack', 'json']}


def test_project_endpoint(celery_worker):
    # celery tests here.
    pass