import argparse
import json
import os
import uuid

import httpx
import marshmallow as ma
import tornado.ioloop
import tornado.web

from cs_workers.utils import clean
from cs_workers.clients import job, api_task


CS_URL = os.environ.get("CS_URL")


class Payload(ma.Schema):
    task_id = ma.fields.UUID(required=False)
    task_name = ma.fields.Str(required=True)
    task_kwargs = ma.fields.Dict(
        keys=ma.fields.Str(), values=ma.fields.Field(), missing=dict
    )


def get_projects():
    resp = httpx.get(f"{CS_URL}/publish/api/")
    assert resp.status_code == 200, f"Got code: {resp.status_code}"
    projects = {}
    for project in resp.json():
        projects[(project["owner"], project["title"])] = project
    return projects


class Scheduler(tornado.web.RequestHandler):
    def initialize(self, projects=None):
        self.projects = projects

    async def post(self, owner, title):
        print("POST -- /", owner, title)
        if not self.request.body:
            return
        payload = Payload().loads(self.request.body.decode("utf-8"))

        if (owner, title) not in self.projects:
            self.set_status(404)

        task_id = payload.get("task_id")
        if task_id is None:
            task_id = uuid.uuid4()
        task_id = str(task_id)
        task_name = payload["task_name"]
        task_kwargs = payload["task_kwargs"]

        if task_name in ("version", "defaults"):
            client = api_task.APITask(
                owner, title, task_id=task_id, task_name=task_name, **task_kwargs
            )
            resp = await client.create(asynchronous=False)
            print(resp.text)
            assert resp.status_code == 200, f"Got code: {resp.status_code}"
            data = resp.json()
        elif task_name in ("parse",):
            client = api_task.APITask(
                owner, title, task_id=task_id, task_name=task_name, **task_kwargs
            )
            resp = await client.create(asynchronous=True)
            assert resp.status_code == 200, f"Got code: {resp.status_code}"

            data = resp.json()
        elif task_name == "sim":
            client = job.Job(
                "cs-workers-dev",
                owner,
                title,
                tag="latest",
                job_id=task_id,
                job_kwargs=payload["task_kwargs"],
            )
            client.create()
            data = {"task_id": client.job_id}
        else:
            self.set_status(404)
            return

        self.write(data)


def get_app():
    return tornado.web.Application(
        [
            (
                r"/([A-Za-z0-9-]+)/([A-Za-z0-9-]+)/",
                Scheduler,
                dict(projects=get_projects()),
            )
        ],
        debug=True,
        autoreload=True,
    )


def start(args: argparse.Namespace):
    if args.start:
        app = get_app()
        app.listen(8888)
        tornado.ioloop.IOLoop.current().start()


def cli(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser(
        "scheduler", description="REST API for running jobs on C/S workers."
    )
    parser.add_argument("--start", required=False, action="store_true")
    parser.set_defaults(func=start)
