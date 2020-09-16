import re
from contextlib import contextmanager

from django.contrib.auth import get_user_model

import requests_mock

from webapp.apps.users.models import Cluster, create_profile_from_user, Profile


User = get_user_model()


@contextmanager
def mock_post_to_cluster():
    matcher = re.compile(Cluster.objects.default().url)
    with requests_mock.Mocker(real_http=True) as mock:
        mock.register_uri("POST", matcher, json={})
        mock.register_uri("GET", matcher, json={})
        yield


def gen_collabs(n):
    for i in range(n):
        u = User.objects.create_user(
            f"collab-{i}", f"collab{i}@example.com", "heyhey2222"
        )
        create_profile_from_user(u)
        yield Profile.objects.get(user__username=f"collab-{i}")
