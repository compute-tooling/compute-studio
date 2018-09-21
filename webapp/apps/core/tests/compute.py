import os
import requests_mock
import json

from webapp.apps.core.compute import Compute


dummy_uuid = "42424200-0000-0000-0000-000000000000"

class MockCompute(Compute):
    outputs = None

    def __init__(self, num_times_to_wait=0):
        self.count = 0
        self.num_times_to_wait = num_times_to_wait

    def remote_submit_job(self, url, data, timeout, headers=None):
        with requests_mock.Mocker() as mock:
            resp = {'job_id': dummy_uuid, 'qlength': 2}
            resp = json.dumps(resp)
            mock.register_uri('POST', url, text=resp)
            self.last_posted = data
            return Compute.remote_submit_job(self, url, data, timeout)

    def remote_query_job(self, url, params):
        with requests_mock.Mocker() as mock:
            if self.num_times_to_wait > 0:
                text = 'NO'
            else:
                text='YES'
            mock.register_uri('GET', url, text=text)
            self.num_times_to_wait -= 1
            return Compute.remote_query_job(self, url, params)

    def remote_get_job(self, url, params):
        self.count += 1
        with requests_mock.Mocker() as mock:
            mock.register_uri('GET', url, text=self.outputs)
            return Compute.remote_get_job(self, url, params)

    def reset_count(self):
        """
        reset worker node count
        """
        self.count = 0
