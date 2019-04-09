import time

from api.celery_app import celery_app, task_wrapper


@celery_app.task(name="error_app_tasks.inputs_get", soft_time_limit=10)
@task_wrapper
def inputs_get(**kwargs):
    start = time.time()

    #######################################
    # code snippet
    def package_defaults(**meta_parameters):
        print("running")
        time.sleep(0.2)
        return 1 / 0

    #######################################
    print("check", kwargs)
    return package_defaults(**kwargs)


@celery_app.task(name="error_app_tasks.inputs_parse", soft_time_limit=10)
@task_wrapper
def inputs_parse(**kwargs):
    start = time.time()

    #######################################
    # code snippet
    def parse_user_inputs(params, jsonparams, errors_warnings, **meta_parameters):
        # parse the params, jsonparams, and errors_warnings further
        time.sleep(0.2)
        return 1 / 0

    #######################################

    return parse_user_inputs(**kwargs)


@celery_app.task(name="error_app_tasks.sim", soft_time_limit=60)
@task_wrapper
def sim(**kwargs):
    start = time.time()

    #######################################
    # code snippet
    def run(**kwargs):
        time.sleep(0.2)
        return 1 / 0

    #######################################

    result = run(**kwargs)

    finish = time.time()
    result["meta"]["task_times"] = [finish - start]
    print("finished result")
    return result
