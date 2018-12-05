import time

from api.celery_app import celery_app, postprocess

@celery_app.task(name='taxcalc_tasks.taxcalc_task', soft_time_limit=40)
def taxcalc_task(year_n, user_mods, start_year, data_source,
                 use_full_sample):
    import taxcalc
    start = time.time()
    print('running task')
    print(
        'taxcalc keywords: ',
        dict(
            year_n=year_n,
            start_year=int(start_year),
            data_source=data_source,
            use_full_sample=use_full_sample,
            user_mods=user_mods
        )
    )

    raw_data = taxcalc.tbi.run_nth_year_taxcalc_model(
        year_n=year_n,
        start_year=int(start_year),
        data_source=data_source,
        use_full_sample=use_full_sample,
        user_mods=user_mods
    )
    finish = time.time()
    raw_data['task_time'] = [finish - start, ]
    return raw_data


@celery_app.task(name='taxcalc_tasks.taxcalc_postprocess', soft_time_limit=10)
def taxcalc_postprocess(ans):
    import taxcalc
    return postprocess(ans, taxcalc.tbi.postprocess)
