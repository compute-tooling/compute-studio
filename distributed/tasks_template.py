import time
import os

from api.celery_app import celery_app, task_wrapper

try:
    import compconfig
except ImportError as ie:
    if os.environ.get("IS_FLASK", "False") == "True":
        compconfig = None
    else:
        raise ie


@celery_app.task(name="{{APP_NAME}}.inputs_get", soft_time_limit=10, bind=True)
@task_wrapper
def inputs_get(self, meta_param_dict):
    return compconfig.get_inputs(meta_param_dict)


@celery_app.task(name="{{APP_NAME}}.inputs_parse", soft_time_limit=10, bind=True)
@task_wrapper
def inputs_parse(self, meta_param_dict, adjustment, errors_warnings):
    return compconfig.validate_inputs(meta_param_dict, adjustment, errors_warnings)


@celery_app.task(name="{{APP_NAME}}.sim", soft_time_limit={{SIM_TIME_LIMIT}}, bind=True)
@task_wrapper
def sim(self, meta_param_dict, adjustment):
    return compconfig.run_model(meta_param_dict, adjustment)
