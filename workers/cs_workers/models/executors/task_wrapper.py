import time
import traceback

import httpx
import cs_storage


try:
    from cs_config import functions
except ImportError as ie:
    pass


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
            async with httpx.AsyncClient() as client:
                resp = await client.get(callback_url)
            resp.raise_for_status()
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
