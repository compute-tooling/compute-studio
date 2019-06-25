import os
import requests
import json
from requests.exceptions import RequestException, Timeout
import requests_mock

requests_mock.Mocker.TEST_PREFIX = "test"

WORKER_HN = os.environ.get("WORKERS")
TIMEOUT_IN_SECONDS = 2.0
MAX_ATTEMPTS_SUBMIT_JOB = 20


class JobFailError(Exception):
    """An Exception to raise when a remote jobs has failed"""


class WorkersUnreachableError(Exception):
    """
    An Exception to raise when the backend workers are not reachable. This
    should only be raised when the webapp is run without the workers.
    """


class Compute(object):
    def remote_submit_job(self, url, data, timeout=TIMEOUT_IN_SECONDS, headers=None):
        response = requests.post(url, data=data, timeout=timeout)
        return response

    def remote_query_job(self, theurl, params):
        job_response = requests.get(theurl, params=params)
        return job_response

    def remote_get_job(self, theurl, params):
        job_response = requests.get(theurl, params=params)
        return job_response

    def submit_job(self, tasks, endpoint):
        print("submitting", tasks, endpoint)
        url = f"http://{WORKER_HN}/{endpoint}"
        return self.submit(tasks, url)

    def submit(self, tasks, url, increment_counter=True, use_wnc_offset=True):
        queue_length = 0
        submitted = False
        attempts = 0
        while not submitted:
            packed = json.dumps(tasks)
            try:
                response = self.remote_submit_job(
                    url, data=packed, timeout=TIMEOUT_IN_SECONDS
                )
                if response.status_code == 200:
                    print("submitted: ", url)
                    submitted = True
                    data = response.json()
                    job_id = data["job_id"]
                    queue_length = data["qlength"]
                else:
                    print("FAILED: ", WORKER_HN)
                    attempts += 1
            except Timeout:
                print("Couldn't submit to: ", WORKER_HN)
                attempts += 1
            except RequestException as re:
                print("Something unexpected happened: ", re)
                attempts += 1
            if attempts > MAX_ATTEMPTS_SUBMIT_JOB:
                print("Exceeded max attempts. Bailing out.")
                raise WorkersUnreachableError()

        return job_id, queue_length

    def results_ready(self, job_id):
        result_url = f"http://{WORKER_HN}/query_job"
        job_response = self.remote_query_job(result_url, params={"job_id": job_id})
        msg = "{0} failed on host: {1}".format(job_id, WORKER_HN)
        if job_response.status_code == 200:  # Valid response
            return job_response.text
        else:
            print("did not expect response with status_code", job_response.status_code)
            raise JobFailError(msg)

    def get_results(self, job_id):
        result_url = f"http://{WORKER_HN}/get_job"
        job_response = self.remote_get_job(result_url, params={"job_id": job_id})
        if job_response.status_code == 200:  # Valid response
            try:
                return job_response.json()
            except ValueError:
                # Got back a bad response. Get the text and re-raise
                msg = "PROBLEM WITH RESPONSE. TEXT RECEIVED: {}"
                raise ValueError(msg)
        else:
            raise WorkersUnreachableError()


class SyncCompute(Compute):
    def submit(self, tasks, url, increment_counter=True, use_wnc_offset=True):
        queue_length = 0
        submitted = False
        attempts = 0
        while not submitted:
            packed = json.dumps(tasks)
            try:
                response = self.remote_submit_job(
                    url, data=packed, timeout=TIMEOUT_IN_SECONDS
                )
                if response.status_code == 200:
                    print("submitted: ", url)
                    submitted = True
                    data = response.json()
                else:
                    print("FAILED: ", WORKER_HN)
                    attempts += 1
            except Timeout:
                print("Couldn't submit to: ", WORKER_HN)
                attempts += 1
            except RequestException as re:
                print("Something unexpected happened: ", re)
                attempts += 1
            if attempts > MAX_ATTEMPTS_SUBMIT_JOB:
                print("Exceeded max attempts. Bailing out.")
                raise WorkersUnreachableError()

        success = data["status"] == "SUCCESS"
        if success:
            return success, data["result"]
        else:
            return success, data["traceback"]
