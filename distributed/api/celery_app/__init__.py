import os
import time
from collections import defaultdict

from celery import Celery

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL',
                                   'redis://localhost:6379')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND',
                                       'redis://localhost:6379')

task_routes = {
    'taxcalc_tasks.*': {'queue': 'taxcalc_queue'},
    'compbaseball_tasks.*': {'queue': 'compbaseball_queue'},
}


celery_app = Celery('tasks2', broker=CELERY_BROKER_URL,
                    backend=CELERY_RESULT_BACKEND)
celery_app.conf.update(
    task_serializer='json',
    accept_content=['msgpack', 'json'],
    task_routes=task_routes,
)


def postprocess(ans, postprocess_func):
    start = time.time()
    all_to_process = defaultdict(list)
    task_times = []
    for result in ans.copy():
        task_times += result.pop('task_time')
        for key, value in result.items():
            all_to_process[key] += value
    results = postprocess_func(all_to_process)
    finish = time.time()
    task_times.append(finish - start)
    results['meta'] = {'task_times': task_times}
    return results
