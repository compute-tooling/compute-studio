import time

from api.celery_app import celery_app

@celery_app.task(name='compbaseball_tasks.compbaseball_task', soft_time_limit=40)
def compbaseball_task(*args):
    pass

@celery_app.task(name='compbaseball_tasks.compbaseball_postprocess', soft_time_limit=10)
def compbaseball_postprocess(ans):
    pass