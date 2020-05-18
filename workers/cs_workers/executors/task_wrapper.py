import functools
import json
import os
import re
import time
import traceback

import redis
import requests
import cs_storage

from cs_workers.utils import redis_conn_from_env


redis_conn = dict(
    username="executor",
    password=os.environ.get("REDIS_EXECUTOR_PW"),
    **redis_conn_from_env(),
)


try:
    from cs_config import functions
except ImportError as ie:
    # if os.environ.get("IS_FLASK", "False") == "True":
    #     functions = None
    # else:
    #     raise ie
    pass


def sync_task_wrapper(task_id, func, **task_kwargs):
    start = time.time()
    traceback_str = None
    res = {}
    try:
        outputs = func(task_id, **task_kwargs)
        res.update(outputs)
    except Exception:
        traceback_str = traceback.format_exc()
    finish = time.time()
    if "meta" not in res:
        res["meta"] = {}
    res["meta"]["task_times"] = [finish - start]
    if traceback_str is None:
        res["status"] = "SUCCESS"
    else:
        res["status"] = "FAIL"
        res["traceback"] = traceback_str
    return res


def async_task_wrapper(task_id, func, **task_kwargs):
    print("sim task", task_id, func)
    start = time.time()
    traceback_str = None
    res = {"job_id": task_id}
    try:
        print("calling func", func)
        if not task_kwargs:
            with redis.Redis(**redis_conn) as rclient:
                task_kwargs = rclient.get(task_id)
            if task_kwargs is None:
                raise KeyError(f"No value found for job id: {task_id}")
        task_kwargs = json.loads(task_kwargs.decode())
        outputs = func(task_id, **task_kwargs)
        res.update(
            {
                "model_version": functions.get_version(),
                "outputs": outputs,
                "version": "v1",
            }
        )
    except Exception:
        traceback_str = traceback.format_exc()
    finish = time.time()
    if "meta" not in res:
        res["meta"] = {}
    res["meta"]["task_times"] = [finish - start]
    if traceback_str is None:
        res["status"] = "SUCCESS"
    else:
        res["status"] = "FAIL"
        res["traceback"] = traceback_str
    print("saving results...")
    resp = requests.post(
        "http://outputs-processor/push/", json={"task_name": "sim", "result": res}
    )
    print("resp", resp.status_code, resp.url)
    assert resp.status_code == 200, f"Got code: {resp.status_code}"

    return res
