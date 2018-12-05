import pytest
from celery import chord

from api.celery_tasks import (taxcalc_task, taxcalc_postprocess)

@pytest.fixture(scope='session')
def celery_config():
    return {
        'broker_url': 'redis://localhost:6379',
        'result_backend': 'redis://localhost:6379',
        'task_serializer': 'json',
        'accept_content': ['msgpack', 'json']}


def test_taxcalc_endpoint(celery_worker):
    tc_params = {
        'user_mods': {
            "policy": {
                2017: {"_FICA_ss_trt": [0.1]}},
            "consumption": {},
            "behavior": {},
            "growdiff_baseline": {},
            "growdiff_response": {},
            "growmodel": {}
        },
        'start_year': 2017,
        'data_source': "CPS",
        'year_n': 0,
        'use_full_sample': False
    }
    inputs = []
    for i in range(0, 3):
        inputs.append(dict(tc_params, **{'year_n': i}))
    compute_task = taxcalc_task
    postprocess_task = taxcalc_postprocess
    result = (chord(compute_task.signature(kwargs=i, serializer='msgpack')
                    for i in inputs))(postprocess_task.signature(
                        serializer='msgpack'))
    assert result.get()
