import os
import time
import traceback

import httpx


try:
    from cs_config import functions
except ImportError as ie:
    pass


async def get_task_kwargs(callback_url, retries=5):
    """
    Retrieve task kwargs from callback_url.

    Returns
    -------
        resp: httpx.Response
    """
    job_token = os.environ.get("JOB_TOKEN", None)
    if job_token is not None:
        headers = {"Authorization": f"Token {job_token}"}
    else:
        headers = None

    for retry in range(0, retries + 1):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(callback_url, headers=headers)
            resp.raise_for_status()
            return resp
        except Exception as e:
            print(f"Exception when retrieving value from callback url: {callback_url}")
            print(f"Exception: {e}")
            if retry >= retries:
                raise e
            wait_time = 2 ** retry
            print(f"Trying again in {wait_time} seconds.")
            time.sleep(wait_time)


async def task_wrapper(callback_url, task_name, func, task_kwargs=None):
    print("async task", callback_url, func, task_kwargs)
    start = time.time()
    traceback_str = None
    res = {
        "task_name": task_name,
    }
    try:
        if task_kwargs is None:
            print("getting task_kwargs")
            resp = await get_task_kwargs(callback_url)
            task_kwargs = resp.json()["inputs"]
        print("got task_kwargs", task_kwargs)
        outputs = func(**(task_kwargs or {}))
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
        resp = await client.post(callback_url, json=res, timeout=120)

    print("resp", resp.status_code, resp.url)
    assert resp.status_code in (200, 201), f"Got code: {resp.status_code} ({resp.text})"

    return res
