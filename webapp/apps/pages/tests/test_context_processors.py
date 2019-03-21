import pytest

from webapp.apps.users.models import Project
from webapp.apps.pages.context_processors import project_list


@pytest.mark.django_db
def test_project_list():
    projs = project_list(None)
    assert projs
    assert len(projs["project_list"]) == Project.objects.count()
    assert isinstance(projs, dict)
    mu = ("hdoupe", "Matchups", "/hdoupe/Matchups/")
    assert mu in projs["project_list"]
