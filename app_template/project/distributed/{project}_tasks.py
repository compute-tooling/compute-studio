import time

from api.celery_app import celery_app

@celery_app.task(name='{project}_tasks.{project}_task', soft_time_limit=40)
def {project}_task(*args):
    pass

@celery_app.task(name='{project}_tasks.{project}_postprocess', soft_time_limit=10)
def {project}_postprocess(ans):
    pass