import os
import time
import traceback
from functools import partial

import cs_storage
import requests
from distributed import worker_client

try:
    from cs_config import functions
except ImportError:
    functions = None


def done_callback(future, job_id, cs_url, cs_api_token, start_time):
    """
    This should be called like:

    callback = functools.partial(
        done_callback,
        job_id=job_id,
        cs_url=os.environ.get("CS_URL"),
        cs_api_token=os.environ.get("CS_API_TOKEN"),
        start_time=time.time()
    )

    This is because this function needs the job id, comp url,
    api token, and start time arguments, but dask only passes the
    future object.
    """
    finish = time.time()
    print(f"job_id: {job_id}")
    print(f"from dask")
    print(f"state: {future.status}")
    res = {}
    traceback_str = None
    try:
        outputs = future.result()
        outputs = cs_storage.write(job_id, outputs)
        res.update(
            {
                "model_version": functions.get_version(),
                "outputs": outputs,
                "version": "v1",
            }
        )
    except Exception:
        traceback_str = traceback.format_exc()
        print(f"exception in callback with job_id: {job_id}")
        print(traceback_str)

    if "meta" not in res:
        res["meta"] = {}
    res["meta"]["task_times"] = [finish - start_time]
    if traceback_str is None:
        res["status"] = "SUCCESS"
    else:
        res["status"] = "FAIL"
        res["traceback"] = traceback_str

    res["job_id"] = job_id
    print("got result", res)
    print(f"posting data to {cs_url}/outputs/api/")
    resp = requests.put(
        f"{cs_url}/outputs/api/",
        json=res,
        headers={"Authorization": f"Token {cs_api_token}"},
    )
    print("resp", resp.status_code)
    if resp.status_code == 400:
        print("errors", resp.json())


def dask_sim(meta_param_dict, adjustment, job_id, cs_url, cs_api_token, timeout):
    """
    Wraps the functions.run_model function with a dask future and adds a
    callback for pushing the results back to the webapp. The callback is
    necessary becuase it will be called no matter what kinds of exceptions
    are thrown in this function.

    This wrapper function is called with fire_and_forget. Since dask
    "forgets" about this function but keeps track of the run_model task,
    we give the run_model task the job_id. This makes it possible for the
    webapp to query the job status.
    """
    start_time = time.time()
    partialled_cb = partial(
        done_callback,
        job_id=job_id,
        cs_url=cs_url,
        cs_api_token=cs_api_token,
        start_time=start_time,
    )
    with worker_client() as c:
        print("c", c)
        fut = c.submit(functions.run_model, meta_param_dict, adjustment, key=job_id)
        fut.add_done_callback(partialled_cb)
        try:
            print("waiting on future", fut)
            _ = fut.result(timeout=timeout)
        except Exception:
            # Exceptions are picked up by the callback. We just
            # log them here.
            traceback_str = traceback.format_exc()
            print(f"exception in task with job_id: {job_id}")
            print(traceback_str)
