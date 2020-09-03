import re
from contextlib import contextmanager

import requests_mock

from webapp.apps.users.models import Cluster


@contextmanager
def mock_post_to_cluster():
    matcher = re.compile(Cluster.objects.default().url)
    with requests_mock.Mocker(real_http=True) as mock:
        mock.register_uri("POST", matcher, json={})
        yield
