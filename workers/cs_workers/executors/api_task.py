import argparse
import json
import os
import uuid

from cs_workers.executors.task_wrapper import async_task_wrapper, sync_task_wrapper

import tornado.ioloop
import tornado.web
from dask.distributed import Client, fire_and_forget

try:
    from cs_config import functions
except ImportError as ie:
    None


def version(task_id, **task_kwargs):
    return {"version": functions.get_version()}


def defaults(task_id, meta_param_dict=None, **task_kwargs):
    return functions.get_inputs(meta_param_dict)


def parse(task_id, meta_param_dict, adjustment, errors_warnings):
    return functions.validate_inputs(meta_param_dict, adjustment, errors_warnings)


class Async(tornado.web.RequestHandler):
    def initialize(self, routes):
        self.routes = routes

    async def post(self, task_name):
        print("POST -- /async/", task_name)
        if task_name not in self.routes:
            self.set_status(404)
            return

        handler = self.routes[task_name]
        payload = json.loads(self.request.body.decode("utf-8"))
        task_id = payload.pop("task_id", None)
        if task_name is None:
            task_id = str(uuid.uuid4())
        async with Client(asynchronous=True, processes=True) as client:
            fut = client.submit(async_task_wrapper, task_id, handler, **payload)
            fire_and_forget(fut)
        self.set_status(200)
        self.write({"status": "PENDING", "task_id": task_name})


class Sync(tornado.web.RequestHandler):
    def initialize(self, routes):
        self.routes = routes

    async def post(self, task_name):
        print("POST -- /sync/", task_name)
        if task_name not in self.routes:
            self.set_status(404)
            return

        handler = self.routes[task_name]
        payload = json.loads(self.request.body.decode("utf-8"))
        task_id = payload.pop("task_id", None)
        if task_name is None:
            task_id = str(uuid.uuid4())
        print("payload", payload)
        result = sync_task_wrapper(task_id, handler, **payload)
        self.write(result)


def executor(routes):
    print("routes", routes)
    return tornado.web.Application(
        [
            (r"/async/([A-Za-z0-9-]+)/", Async, dict(routes=routes)),
            (r"/sync/([A-Za-z0-9-]+)/", Sync, dict(routes=routes)),
        ],
        debug=True,
        autoreload=True,
    )


def start(args: argparse.Namespace):
    if args.start:
        app = executor(
            routes={"version": version, "defaults": defaults, "parse": parse}
        )
        app.listen(8888)
        tornado.ioloop.IOLoop.current().start()


def cli(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser(
        "api-task", description="REST API for running light-weight tasks."
    )
    parser.add_argument("--start", required=False, action="store_true")
    parser.set_defaults(func=start)
