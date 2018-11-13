import json
import os
import time
from io import BytesIO
from collections import defaultdict

import taxcalc

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
    formatted['meta'] = {'job_times': [f - t, ]}
    return json.dumps(formatted)


def postprocess(ans, postprocess_func):
    start = time.time()
    all_to_process = defaultdict(list)
    job_times = []
    for year_data in ans.copy():
        job_times += year_data.pop('job_time')
        for key, value in year_data.items():
            all_to_process[key] += value
    results = postprocess_func(all_to_process)
    # Add taxcalc version to results
    vinfo = taxcalc._version.get_versions()
    results['taxcalc_version'] = vinfo['version']
    # TODO: Make this the distributed app version, not the TC version
    finish = time.time()
    job_times.append(finish - start)
    results['meta'] = {'job_times': job_times}
    return json.dumps(results)


@celery_app.task(name='api.celery_tasks.taxcalc_task', soft_time_limit=40)
def taxcalc_task(year_n, user_mods, start_year, use_puf_not_cps,
                 use_full_sample):
    start = time.time()
    print('running task')
    print(
        'taxcalc keywords: ',
        dict(
            year_n=year_n,
            start_year=int(start_year),
            use_puf_not_cps=use_puf_not_cps,
            use_full_sample=use_full_sample,
            user_mods=user_mods
        )
    )

    raw_data = taxcalc.tbi.run_nth_year_taxcalc_model(
        year_n=year_n,
        start_year=int(start_year),
        use_puf_not_cps=use_puf_not_cps,
        use_full_sample=use_full_sample,
        user_mods=user_mods
    )
    finish = time.time()
    raw_data['job_time'] = [finish - start, ]
    return raw_data


@celery_app.task(name='api.celery_tasks.taxcalc_postprocess', soft_time_limit=10)
def taxcalc_postprocess(ans):
    return postprocess(ans, taxcalc.tbi.postprocess)
