from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory

import pytest

from webapp.apps.users.models import Project
from webapp.apps.pages.context_processors import project_list


@pytest.mark.django_db
def test_project_list():
    request = RequestFactory().get("/")
    request.user = AnonymousUser()

    projs = project_list(request)
    assert projs
    assert len(projs["project_list"]) == Project.objects.filter(listed=True).count()
    assert isinstance(projs, dict)
    mu = ("hdoupe", "Matchups", "/hdoupe/Matchups/")
    assert mu in projs["project_list"]

    project = Project.objects.get(owner__user__username="hdoupe", title="Matchups")
    project.is_public = False
    project.listed = True
    project.save()
    projs = project_list(request)
    assert mu not in projs["project_list"]

    request.user = project.owner.user
    projs = project_list(request)
    assert mu in projs["project_list"]
