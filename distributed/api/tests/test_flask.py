import pytest
import json
import time
import msgpack

from api import create_app


@pytest.fixture
def app():
    app = create_app({'TESTING': True})

    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def post_and_poll(client, url, data, exp_status='YES', tries=30):
    packed = msgpack.dumps(data, use_bin_type=True)
    resp = client.post(url,
                       data=packed,
                       headers={'Content-Type': 'application/octet-stream'}
                       )
    assert resp.status_code == 200
    data = json.loads(resp.data.decode('utf-8'))
    job_id = data['job_id']
    status = 'NO'
    while status == 'NO' and tries > 0:
        resp = client.get(
            '/query_job?job_id={job_id}'.format(job_id=job_id)
        )
        status = resp.data.decode('utf-8')
        assert resp.status_code == 200
        time.sleep(1)
        tries -= 1

    assert status == exp_status

    resp = client.get(
        '/get_job?job_id={job_id}'.format(job_id=job_id)
    )
    assert resp.status_code == 200
    return resp


def test_hello(client):
    resp = client.get('/hello')
    print(resp)