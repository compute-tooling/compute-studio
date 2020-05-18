import os
import requests_mock
import json
import uuid

from rest_framework.test import APIClient

from webapp.apps.comp.compute import Compute


class CallbackException(Exception):
    pass


class MockCompute(Compute):
    outputs = None
    client = None
    sim = None
    user = "comp-api-user"
    password = "heyhey2222"

    def __init__(self, num_times_to_wait=0):
        self.count = 0
        self.num_times_to_wait = num_times_to_wait

    def remote_submit_job(self, url, data, timeout, headers=None):
        print("mocking:", url)
        with requests_mock.Mocker() as mock:
            resp = {"job_id": str(uuid.uuid4()), "qlength": 2}
            resp = json.dumps(resp)
            print("mocking", url)
            mock.register_uri("POST", url, text=resp)
            self.last_posted = data
            return Compute.remote_submit_job(self, url, data, timeout)

    def remote_query_job(self, url):
        # Need to login as the comp-api-user
        self.client.login(username=self.user, password=self.password)
        if isinstance(self.client, APIClient):
            format_kwarg = {"format": "json"}
        else:
            format_kwarg = {"content_type": "application/json"}
        resp = self.client.put(
            "/outputs/api/",
            data=dict(json.loads(self.outputs), **{"job_id": self.sim.job_id}),
            **format_kwarg,
        )
        if resp.status_code != 200:
            raise CallbackException(
                f"Status code: {resp.status_code}\n {json.dumps(resp.data, indent=4)}"
            )
        self.client = None
        self.sim = None
        with requests_mock.Mocker() as mock:
            text = "NO"
            mock.register_uri("GET", url, text=text)
            return Compute.remote_query_job(self, url)

    def remote_get_job(self, url):
        self.count += 1
        with requests_mock.Mocker() as mock:
            mock.register_uri("GET", url, text=self.outputs)
            return Compute.remote_get_job(self, url)

    def reset_count(self):
        """
        reset worker node count
        """
        self.count = 0


class MockComputeWorkerFailure(MockCompute):
    next_response = None
    outputs = json.dumps({"status": "WORKER_FAILURE", "traceback": "Error: whoops"})

    def remote_query_job(self, url):
        self.client = None
        self.sim = None
        with requests_mock.Mocker() as mock:
            print("mocking: ", url)
            text = "FAIL"
            mock.register_uri("GET", url, text=text)
            return Compute.remote_query_job(self, url)
