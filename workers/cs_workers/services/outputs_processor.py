import argparse
import json
import os

import httpx
import redis
import tornado.ioloop
import tornado.web

try:
    from dask.distributed import Client
except ImportError:
    Client = None

import cs_storage

from cs_workers.services import auth
from cs_workers.utils import redis_conn_from_env


redis_conn = dict(
    username=os.environ.get("REDIS_USER"),
    password=os.environ.get("REDIS_PW"),
    **redis_conn_from_env(),
)


BUCKET = os.environ.get("BUCKET")


async def write(task_id, outputs):
    async with await Client(asynchronous=True, processes=False) as client:
        outputs = cs_storage.deserialize_from_json(outputs)
        res = await client.submit(cs_storage.write, task_id, outputs)
    return res


async def push(url, auth_headers, task_name, result):
    async with httpx.AsyncClient(headers=auth_headers) as client:
        if task_name == "sim":
            print(f"posting data to {url}/outputs/api/")
            return await client.put(f"{url}/outputs/api/", json=result)
        if task_name == "parse":
            print(f"posting data to {url}/inputs/api/")
            return await client.put(f"{url}/inputs/api/", json=result)
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
        data = json.loads(self.request.body.decode("utf-8"))
        job_id = data.get("result", {}).get("task_id", None)
        if job_id is None:
            print("missing job id")
            self.set_status(400)
            self.write(json.dumps({"error": "Missing job id."}))
            return

        with redis.Redis(**redis_conn) as rclient:
            data = rclient.get(f"jobinfo-{job_id}")

        if data is None:
            print("Unknown job id: ", job_id)
            self.set_status(400)
            self.write(json.dumps({"error": "Unknown job id."}))
            return

        jobinfo = json.loads(data.decode())
        print("got jobinfo", jobinfo)
        cluster_user = jobinfo.get("cluster_user", None)
        if cluster_user is None:
            print("missing Cluster-User")
            self.set_status(400)
            self.write(json.dumps({"error": "Missing cluster_user."}))
            return
        user = auth.User.get(cluster_user)
        if user is None:
            print("unknown user", cluster_user)
            self.set_status(404)
            return

        print("got user", user.username, user.url)

        payload = json.loads(self.request.body.decode("utf-8"))
        resp = await push(url=user.url, auth_headers=user.headers(), **payload)
        print("got resp-push", resp.status_code, resp.url)
        self.set_status(200)


def get_app():
    assert Client is not None, "Unable to import dask client"
    assert auth.cryptkeeper is not None
    assert BUCKET
    return tornado.web.Application([(r"/write/", Write), (r"/push/", Push)])


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
