import pytest
import re
from contextlib import contextmanager

from django.contrib.auth import get_user_model

import requests_mock

from webapp.apps.users.models import Cluster, create_profile_from_user, Profile


User = get_user_model()


def gen_collabs(n):
    for i in range(n):
        u = User.objects.create_user(
            f"collab-{i}", f"collab{i}@example.com", "heyhey2222"
        )
        create_profile_from_user(u)
        yield Profile.objects.get(user__username=f"collab-{i}")
