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
    cluster = None

    def __init__(self, num_times_to_wait=0):
        self.count = 0
        self.num_times_to_wait = num_times_to_wait

    def remote_submit_job(self, url, data, timeout, headers=None):
        print("mocking:", url)
        with requests_mock.Mocker() as mock:
            resp = {"task_id": str(uuid.uuid4())}
            resp = json.dumps(resp)
            print("mocking", url)
            mock.register_uri("POST", url, text=resp)
            self.last_posted = data
            return Compute.remote_submit_job(self, url, data, timeout)

    def reset_count(self):
        """
        reset worker node count
        """
        self.count = 0
