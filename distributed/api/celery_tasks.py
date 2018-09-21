import json
import os
from io import BytesIO
import time

from celery import Celery

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL',
                                   'redis://localhost:6379')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND',
                                       'redis://localhost:6379')

celery_app = Celery('tasks2', broker=CELERY_BROKER_URL,
                    backend=CELERY_RESULT_BACKEND)
celery_app.conf.update(
    task_serializer='json',
    accept_content=['msgpack', 'json'],
)

@celery_app.task(name='api.celery_tasks.file_upload_test')
def file_upload_test(data, compression):
    t = time.time()
    import pandas as pd
    df = pd.read_csv(BytesIO(data), compression='gzip')
    desc = df.describe()
    formatted = {'outputs': [], 'aggr_outputs': [], 'meta':{}}
    formatted['aggr_outputs'].append({
        'tags': {'default': 'default'},
        'title': 'desc',
        'downloadable': [{'filename': 'desc' + '.csv',
                            'text': desc.to_csv()}],
        'renderable': desc.to_html()})
    f = time.time()
    formatted['meta'] = {'job_time': (f - t) / 3600, 'n_jobs': 1}
    return json.dumps(formatted)
