import argparse
import json
import os

import httpx
import tornado.ioloop
import tornado.web
from dask.distributed import Client

import cs_storage


CS_URL = os.environ.get("CS_URL")
CS_API_TOKEN = os.environ.get("CS_API_TOKEN")


async def write(task_id, outputs):
    client = await Client(asynchronous=True, processes=False)
    outputs = cs_storage.deserialize_from_json(outputs)
    res = await client.submit(cs_storage.write, task_id, outputs)
    return res


async def push(task_name, result):
    async with httpx.AsyncClient(
        headers={"Authorization": f"Token {CS_API_TOKEN}"}
    ) as client:
        if task_name == "sim":
            print(f"posting data to {CS_URL}/outputs/api/")
            return await client.put(f"{CS_URL}/outputs/api/", json=result)
        if task_name == "parse":
            print(f"posting data to {CS_URL}/inputs/api/")
            return await client.put(f"{CS_URL}/inputs/api/", json=result)
        else:
            raise ValueError(f"Unknown task type: {task_name}.")


class Write(tornado.web.RequestHandler):
    async def post(self):
        print("POST -- /write/")
        payload = json.loads(self.request.body.decode("utf-8"))
        result = await write(**payload)
        print("success-write")
        self.write(result)


class Push(tornado.web.RequestHandler):
    async def post(self):
        print("POST -- /push/")
        payload = json.loads(self.request.body.decode("utf-8"))
        resp = await push(**payload)
        print("got resp-push", resp.status_code, resp.url)
        self.set_status(200)


def get_app():
    return tornado.web.Application(
        [(r"/write/", Write), (r"/push/", Push)], debug=True, autoreload=True
    )


def start(args: argparse.Namespace):
    if args.start:
        app = get_app()
        app.listen(8888)
        tornado.ioloop.IOLoop.current().start()


def cli(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser(
        "outputs-processor",
        aliases=["outputs"],
        description="REST API for processing and storing outputs.",
    )
    parser.add_argument("--start", required=False, action="store_true")
    parser.set_defaults(func=start)
