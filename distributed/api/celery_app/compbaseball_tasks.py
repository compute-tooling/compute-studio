import time

from api.celery_app import celery_app

@celery_app.task(name='compbaseball_tasks.compbaseball_task', soft_time_limit=40)
def compbaseball_task(user_mods):
    from compbaseball import baseball
    start = time.time()
    print('pitching', user_mods)
    result = baseball.get_data(**user_mods["pitching"])
    finish = time.time()
    result["meta"]["task_times"] = [finish - start]
    return result


@celery_app.task(name='compbaseball_tasks.compbaseball_postprocess', soft_time_limit=10)
def compbaseball_postprocess(ans):
    return ans[0]