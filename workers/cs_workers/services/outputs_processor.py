import argparse
import json
import os

import httpx
from pydantic import BaseModel
import redis
from rq import Queue
from fastapi import FastAPI, Body
from .api.schemas import TaskComplete


try:
    from dask.distributed import Client
except ImportError:
    Client = None

import cs_storage


app = FastAPI()

queue = Queue(
    connection=redis.Redis(
        host=os.environ.get("REDIS_HOST"),
        port=os.environ.get("REDIS_PORT"),
        password=os.environ.get("REDIS_PASSWORD"),
    )
)


BUCKET = os.environ.get("BUCKET")


class Result(BaseModel):
    url: str
    headers: dict
    task: TaskComplete


def write(task_id, outputs):
    outputs = cs_storage.deserialize_from_json(outputs)
    res = cs_storage.write(task_id, outputs)
    return res


def push(job_id: str, result: Result):
    resp = None
    if result.task.task_name == "sim":
        print(f"posting data to {result.url}/outputs/api/")
        result.task.outputs = write(job_id, result.task.outputs)
        resp = httpx.put(
            f"{result.url}/outputs/api/",
            json=dict(job_id=job_id, **result.task.dict()),
            headers=result.headers,
        )
    elif result.task.task_name == "parse":
        print(f"posting data to {result.url}/inputs/api/")
        resp = httpx.put(
            f"{result.url}/inputs/api/",
            json=dict(job_id=job_id, **result.task.dict()),
            headers=result.headers,
        )
    elif result.task.task_name == "defaults":
        print(f"posting data to {result.url}/model-config/api/")
        resp = httpx.put(
            f"{result.url}/model-config/api/",
            json=dict(job_id=job_id, **result.task.dict()),
            headers=result.headers,
        )

    if resp is not None and resp.status_code == 400:
        print(resp.text)
        resp.raise_for_status()
    elif resp is not None:
        resp.raise_for_status()
    else:
        raise ValueError(
            f"resp is None for: {job_id} with name {result.task.task_name}"
        )


@app.post("/{job_id}/", status_code=200)
async def post(job_id: str, result: Result = Body(...)):
    print("POST -- /", job_id)
    queue.enqueue(push, job_id, result)
