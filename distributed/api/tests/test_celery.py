# import pytest
# from celery import chord

# @pytest.fixture(scope='session')
# def celery_config():
#     return {
#         'broker_url': 'redis://redis:6379/0',
#         'result_backend': 'redis://redis:6379/0',
#         'task_serializer': 'json',
#         'accept_content': ['msgpack', 'json']}


# def test_project_endpoint(celery_worker):
#     # celery tests here.
#     pass
