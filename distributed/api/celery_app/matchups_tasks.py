import time

from api.celery_app import celery_app

@celery_app.task(name='matchups_tasks.matchups_task', soft_time_limit=60)
def matchups_task(**kwargs):
    start = time.time()

    #######################################
    # code snippet
    import matchups

    def run(**kwargs):
        result = matchups.get_matchup(kwargs["use_full_data"], kwargs["user_mods"])
        return result
    #######################################

    result = run(**kwargs)

    finish = time.time()
    result["meta"]["task_times"] = [finish - start]
    print("finished result")
    return result

@celery_app.task(name='matchups_tasks.matchups_postprocess', soft_time_limit=10)
def matchups_postprocess(ans):
    # do nothing by default
    return ans[0]