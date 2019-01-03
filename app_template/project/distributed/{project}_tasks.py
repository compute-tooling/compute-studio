import time

from api.celery_app import celery_app

@celery_app.task(name='{project}_tasks.{project}_task', soft_time_limit=60)
def {project}_task(*args):
    start = time.time()

    #######################################
    # code snippet

    #######################################

    result = run(*args)

    finish = time.time()
    result["meta"]["task_times"] = [finish - start]
    print("finished result")
    return result

@celery_app.task(name='{project}_tasks.{project}_postprocess', soft_time_limit=10)
def {project}_postprocess(ans):
    # do nothing by default
    return ans[0]