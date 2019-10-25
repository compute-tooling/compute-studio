import os
import time
import traceback
from functools import partial

import cs_storage

print("using cs_storage version", cs_storage.__version__)
import requests
from distributed import Client

try:
    from cs_config import functions
except ImportError:
    functions = None


def done_callback(future, job_id, comp_url, comp_api_token, start_time):
    """
    This should be called like:

    callback = functools.partial(
        done_callback,
        job_id=job_id,
        comp_url=os.environ.get("COMP_URL"),
        comp_api_token=os.environ.get("comp_api_token"),
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
    print(f"posting data to {comp_url}/outputs/api/")
    resp = requests.put(
        f"{comp_url}/outputs/api/",
        json=res,
        headers={"Authorization": f"Token {comp_api_token}"},
    )
    print("resp", resp.status_code)
    if resp.status_code == 400:
        print("errors", resp.json())


def dask_sim(meta_param_dict, adjustment, job_id, comp_url, comp_api_token):
    """
    Wraps the functions.run_model function with a dask future and adds a
    callback for pushing the results back to the webapp. The callback is
    necessary becuase it will be called no matter what kinds of exceptions
    are thrown in this function.
    """
    start_time = time.time()
    partialled_cb = partial(
        done_callback,
        job_id=job_id,
        comp_url=comp_url,
        comp_api_token=comp_api_token,
        start_time=start_time,
    )
    with Client() as c:
        print("c", c)
        # TODO: add and handle timeout
        fut = c.submit(functions.run_model, meta_param_dict, adjustment)
        fut.add_done_callback(partialled_cb)
        try:
            print("waiting on future", fut)
            _ = fut.result()
        except Exception:
            # Exceptions are picked up by the callback. We just
            # log them here.
            traceback_str = traceback.format_exc()
            print("exception executing job", job_id)
            print(traceback_str)
