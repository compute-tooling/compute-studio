import time
from io import BytesIO

from api.celery_app import celery_app

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
    formatted['meta'] = {'task_times': [f - t, ]}
    return formatted
