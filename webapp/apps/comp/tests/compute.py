import os
import requests_mock
import json
import uuid

from webapp.apps.comp.compute import Compute


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
        with requests_mock.Mocker() as mock:
            resp = {"job_id": str(uuid.uuid4()), "qlength": 2}
            resp = json.dumps(resp)
            mock.register_uri("POST", url, text=resp)
            self.last_posted = data
            return Compute.remote_submit_job(self, url, data, timeout)

    def remote_query_job(self, url, params):
        # Need to login as the comp-api-user
        self.client.login(username=self.user, password=self.password)
        resp = self.client.put(
            "/outputs/api/",
            data=dict(json.loads(self.outputs), **{"job_id": self.sim.job_id}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        self.client = None
        self.sim = None
        with requests_mock.Mocker() as mock:
            text = "NO"
            mock.register_uri("GET", url, text=text)
            return Compute.remote_query_job(self, url, params)

    def remote_get_job(self, url, params):
        self.count += 1
        with requests_mock.Mocker() as mock:
            mock.register_uri("GET", url, text=self.outputs)
            return Compute.remote_get_job(self, url, params)

    def reset_count(self):
        """
        reset worker node count
        """
        self.count = 0
