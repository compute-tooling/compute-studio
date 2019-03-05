import pytest

from webapp.apps.pages.context_processors import project_list


@pytest.mark.django_db
def test_project_list():
    projs = project_list(None)
    assert projs
    assert isinstance(projs, dict)
    mu = ("hdoupe", "Matchups", "/hdoupe/Matchups/")
    assert mu in projs["project_list"]
