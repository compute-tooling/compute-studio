import time
import os
import gzip
from collections import defaultdict

from api.celery_app import celery_app, task_wrapper


AWS_ACCESS_KEY_ID = os.environ.pop("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.pop("AWS_SECRET_ACCESS_KEY", "")


@celery_app.task(name="pslmodels_taxbrain_tasks.inputs_get", soft_time_limit=10)
@task_wrapper
def inputs_get(**kwargs):

    #######################################
    # code snippet
    from taxbrain.tbi import get_defaults
    import numpy as np

    def package_defaults(**meta_parameters):
        return get_defaults(**meta_parameters)

    #######################################

    return package_defaults(**kwargs)


@celery_app.task(name="pslmodels_taxbrain_tasks.inputs_parse", soft_time_limit=10)
@task_wrapper
def inputs_parse(**kwargs):

    #######################################
    # code snippet
    from taxbrain.tbi import parse_user_inputs as _parse_user_inputs

    def parse_user_inputs(params, jsonparams, errors_warnings, **valid_meta_params):
        return _parse_user_inputs(
            params, jsonparams, errors_warnings, **valid_meta_params
        )

    #######################################

    return parse_user_inputs(**kwargs)


@celery_app.task(name="pslmodels_taxbrain_tasks.sim", soft_time_limit=400)
@task_wrapper
def sim(**kwargs):
    import boto3
    import pandas as pd

    has_credentials = AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
    if kwargs["data_source"] == "PUF" and has_credentials:
        client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
        obj = client.get_object(Bucket="ospc-data-files", Key="puf.csv.gz")
        gz = gzip.GzipFile(fileobj=obj["Body"])
        puf_df = pd.read_csv(gz)
    else:
        puf_df = None

    #######################################
    # code snippet
    import taxbrain

    def run(start_year, data_source, use_full_sample, user_mods):
        return taxbrain.tbi.run_tbi_model(
            start_year, data_source, use_full_sample, user_mods, puf_df
        )

    #######################################

    return {"outputs": run(**kwargs), "version": "v0"}
