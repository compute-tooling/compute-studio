import time

from api.celery_app import celery_app


@celery_app.task(name="pslmodels_taxbrain_tasks.inputs_get", soft_time_limit=10)
def inputs_get(**kwargs):
    start = time.time()

    #######################################
    # code snippet
    from taxbrain.tbi import get_defaults
    import numpy as np

    def package_defaults(**meta_parameters):
        defaults = get_defaults(**meta_parameters)
        seri = {}
        for param, data in defaults["policy"].items():
            seri[param] = dict(data, **{"value": np.array(data["value"]).tolist()})
        defaults["policy"] = seri
        return defaults

    #######################################

    return package_defaults(**kwargs)


@celery_app.task(name="pslmodels_taxbrain_tasks.inputs_parse", soft_time_limit=10)
def inputs_parse(**kwargs):
    start = time.time()

    #######################################
    # code snippet
    from taxbrain.tbi import parse_user_inputs as _parse_user_inputs

    def parse_user_inputs(params, jsonparams, errors_warnings, **valid_meta_params):
        return _parse_user_inputs(
            params, jsonparams, errors_warnings, **valid_meta_params
        )

    #######################################

    return parse_user_inputs(**kwargs)


@celery_app.task(name="pslmodels_taxbrain_tasks.sim", soft_time_limit=300)
def sim(**kwargs):
    start = time.time()

    #######################################
    # code snippet
    import taxbrain

    def run(start_year, data_source, use_full_sample, user_mods):
        return taxbrain.tbi.run_tbi_model(
            start_year, data_source, use_full_sample, user_mods
        )

    #######################################

    result = run(**kwargs)

    finish = time.time()
    if "meta" not in result:
        result["meta"] = {}
    result["meta"]["task_times"] = [finish - start]
    print("finished result")
    return result
