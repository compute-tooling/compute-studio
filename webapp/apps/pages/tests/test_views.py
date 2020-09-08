import pytest

from django.contrib import auth

from ..views import ABOUT_URL

User = auth.get_user_model()


@pytest.mark.django_db
class TestPageViews:
    def test_home_page_noauth(self, client):
        # check user is redirected if not logged in.
        resp = client.get("/")
        assert resp.status_code == 302, f"Expected 302, got {resp.status_code}"
        assert resp.url == ABOUT_URL

    def test_get_user_profile(
        self, monkeypatch, client, profile, password, test_models
    ):
        resp = client.get(f"/{profile.user.username}/")
        assert resp.status_code == 200

    def test_get_user_does_not_exist(self, client, profile, password):
        resp = client.get(f"/notarealuser/")
        assert resp.status_code == 404

    def test_home_page_auth(self, client):
        # check profile page rendered if logged in
        client.login(username="modeler", password="modeler2222")
        resp = client.get("/")
        assert resp.status_code == 200
        assert "project_list" in resp.context
        assert "profile/home_base.html" in [t.name for t in resp.templates]

    def test_get_pages(self, client):
        for page in ["privacy", "terms", "dmca", "feed"]:
            assert client.get(f"/{page}/").status_code == 200
        resp = client.get("/about/")
        assert resp.status_code == 302, f"Expected 302, got {resp.status_code}"
        assert resp.url == ABOUT_URL

    def test_get_robots(self, client):
        assert client.get(f"/robots.txt").status_code == 200
