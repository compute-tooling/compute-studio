import re
from contextlib import contextmanager

import requests_mock

from webapp.apps.users.models import Cluster


@contextmanager
def mock_sync_projects(project=None):
    if project is None:
        cluster = Cluster.objects.default()
    else:
        cluster = project.cluster
    with requests_mock.Mocker(real_http=True) as mock:
        mock.register_uri("POST", f"{cluster.url}/sync/", json={"status": "SUCCESS"})
        yield


@contextmanager
def mock_get_version():
    matcher = re.compile(Cluster.objects.default().url)
    with requests_mock.Mocker(real_http=True) as mock:
        mock.register_uri("POST", matcher, json={"status": "SUCCESS", "version": "v1"})
        yield
