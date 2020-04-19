import os

import requests
from celery import Celery

import cs_storage


CS_URL = os.environ.get("CS_URL")
CS_API_TOKEN = os.environ.get("CS_API_TOKEN")

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379"
)

app = Celery(
    "outputs_processor", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND
)
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)


@app.task(name="outputs_processor.write_to_storage")
def write(task_id, outputs):
    outputs = cs_storage.deserialize_from_json(outputs)
    res = cs_storage.write(task_id, outputs)
    print(res)
    return res


@app.task(name="outputs_processor.push_to_cs")
def push(task_type, payload):
    if task_type == "sim":
        print(f"posting data to {CS_URL}/outputs/api/")
        resp = requests.put(
            f"{CS_URL}/outputs/api/",
            json=payload,
            headers={"Authorization": f"Token {CS_API_TOKEN}"},
        )
        print("resp", resp.status_code)
        if resp.status_code == 400:
            print("errors", resp.json())
    if task_type == "parse":
        print(f"posting data to {CS_URL}/inputs/api/")
        resp = requests.put(
            f"{CS_URL}/inputs/api/",
            json=payload,
            headers={"Authorization": f"Token {CS_API_TOKEN}"},
        )
        print("resp", resp.status_code)
        if resp.status_code == 400:
            print("errors", resp.json())
