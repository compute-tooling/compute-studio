import asyncio
import functools
import json
import os
import re
import time
import traceback

import redis
import httpx
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


async def sync_task_wrapper(task_id, task_name, func, task_kwargs=None):
    print("sync task", task_id, func, task_kwargs)
    start = time.time()
    traceback_str = None
    res = {}
    try:
        outputs = func(task_id, **(task_kwargs or {}))
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


async def async_task_wrapper(task_id, task_name, func, timeout=None, task_kwargs=None):
    print("async task", task_id, func, task_kwargs)
    start = time.time()
    traceback_str = None
    res = {"task_id": task_id}
    try:
        if task_kwargs is None:
            if not task_id.startswith("job-"):
                _task_id = f"job-{task_id}"
            else:
                _task_id = task_id
            with redis.Redis(**redis_conn) as rclient:
                task_kwargs = rclient.get(_task_id)
            if task_kwargs is not None:
                task_kwargs = json.loads(task_kwargs.decode())

        if timeout:
            loop = asyncio.get_event_loop()
            fut = loop.run_in_executor(None, func, task_id, **(task_kwargs or {}))
            outputs = await asyncio.wait_for(fut, timeout=timeout)
        else:
            outputs = func(task_id, **(task_kwargs or {}))
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
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://outputs-processor/push/",
            json={"task_name": task_name, "result": res},
        )
    print("resp", resp.status_code, resp.url)
    assert resp.status_code == 200, f"Got code: {resp.status_code}"

    return res
