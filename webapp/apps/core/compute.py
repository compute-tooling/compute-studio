import os
import requests
import msgpack
from requests.exceptions import RequestException, Timeout
import requests_mock
requests_mock.Mocker.TEST_PREFIX = 'test'

WORKER_HN = os.environ.get('WORKERS')
TIMEOUT_IN_SECONDS = 1.0
MAX_ATTEMPTS_SUBMIT_JOB = 20
BYTES_HEADER = {'Content-Type': 'application/octet-stream'}


class JobFailError(Exception):
    """An Exception to raise when a remote jobs has failed"""


class WorkersUnreachableError(Exception):
    """
    An Exception to raise when the backend workers are not reachable. This
    should only be raised when the webapp is run without the workers.
    """

class Compute(object):
    def remote_submit_job(
            self,
            url,
            data,
            timeout=TIMEOUT_IN_SECONDS,
            headers=None):
        # print(theurl, data)
        if headers is not None:
            response = requests.post(url,
                                     data=data,
                                     timeout=timeout,
                                     headers=headers)
        else:
            response = requests.post(url, data=data, timeout=timeout)
        return response

    def remote_query_job(self, theurl, params):
        job_response = requests.get(theurl, params=params)
        return job_response

    def remote_get_job(self, theurl, params):
        job_response = requests.get(theurl, params=params)
        return job_response

    def submit_job(self, tasks, endpoint):
        url = f'http://{WORKER_HN}/{endpoint}'
        return self.submit(tasks, url)

    def submit(self,
               tasks,
               url,
               increment_counter=True,
               use_wnc_offset=True):
        queue_length = 0
        submitted = False
        attempts = 0
        while not submitted:
            packed = msgpack.dumps(tasks, use_bin_type=True)
            try:
                response = self.remote_submit_job(
                    url, data=packed, timeout=TIMEOUT_IN_SECONDS,
                    headers=BYTES_HEADER)
                if response.status_code == 200:
                    print("submitted: ", )
                    submitted = True
                    response_d = response.json()
                    job_id = response_d['job_id']
                    queue_length = response_d['qlength']
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
        result_url = f'http://{WORKER_HN}/query_job'
        job_response = self.remote_query_job(
            result_url, params={'job_id': job_id})
        msg = '{0} failed on host: {1}'.format(job_id, WORKER_HN)
        if job_response.status_code == 200:  # Valid response
            return job_response.text
        else:
            print(
                'did not expect response with status_code',
                job_response.status_code)
            raise JobFailError(msg)

    def _get_results_base(self, job_id, job_failure=False):
        result_url = f'http://{WORKER_HN}/get_job'
        job_response = self.remote_get_job(
            result_url,
            params={'job_id': job_id}
        )
        if job_response.status_code == 200:  # Valid response
            try:
                if job_failure:
                    return job_response.text
                else:
                    return job_response.json()
            except ValueError:
                # Got back a bad response. Get the text and re-raise
                msg = 'PROBLEM WITH RESPONSE. TEXT RECEIVED: {}'
                raise ValueError(msg)
        else:
            raise  IOError()

    def get_results(self, job_id, job_failure=False):
        if job_failure:
            return self._get_results_base(job_id, job_failure=job_failure)

        ans = self._get_results_base(job_id, job_failure=job_failure)

        return ans
