import pytest

from django.contrib import auth
from django.urls import reverse

from webapp.apps.users.models import Project


@pytest.mark.django_db
class CoreAbstractViewsTest:
    """
    Abstract test class to be used for efficient testing of modeling projects.
    The approach used here goes against conventional wisdom to use simple,
    stupid test code. This is done because there will be many types of models
    that share a "core" functionality. Re-writing and maintaining many copies
    of the same tests would be cumbersome, time-consuming, and error-prone.
    """

    app_name = "core"
    title = "Core"
    post_data_ok = {}
    mockcompute = None
    RunModel = None

    def test_get(self, monkeypatch, client):
        """
        Test simple get returns 200 status
        """
        resp = client.get(reverse(self.title))
        assert resp.status_code == 200

    def test_logged_in(self, client, profile, password):
        """
        Test simple get returns AnonymousUser and login returns authenticated
        user
        """
        resp = client.get(reverse(self.title))
        assert resp.status_code == 200
        anon_user = auth.get_user(client)
        assert not anon_user.is_authenticated

        assert self.login_client(client, profile.user, password)
        resp = client.get(reverse(self.title))
        assert resp.status_code == 200
        user = auth.get_user(client)
        assert user.is_authenticated

    def test_post(self, monkeypatch, client, password, profile):
        """
        Tests:
        - post with logged-in user returns 302 redirect
        - test render results page returns 200
        - test download page returns 200 and zip file content
        - test logged out user can view outputs page
        """
        monkeypatch.setattr(
            f"webapp.apps.projects.{self.app_name}.views.Compute", self.mockcompute
        )
        monkeypatch.setattr("webapp.apps.core.views.Compute", self.mockcompute)

        self.login_client(client, profile.user, password)
        resp = client.post(reverse(self.title), data=self.inputs_ok())
        assert resp.status_code == 302  # redirect
        idx = resp.url[:-1].rfind("/")
        slug = resp.url[(idx + 1) : -1]
        assert resp.url == f"{reverse(self.title)}{slug}/"

        # test get ouputs page
        resp = client.get(resp.url)
        assert resp.status_code == 200

        # test ouptut download
        resp = client.get(f"{reverse(self.title)}{slug}/download")
        assert resp.status_code == 200
        assert resp._headers["content-type"] == ("Content-Type", "application/zip")

    def test_edit_page(self, monkeypatch, client, password, profile):
        """
        Tests:
        - post with logged-in user returns 302 redirect
        - test render results page returns 200
        - test get edit page

        Note: it would be helpful to do a post with a subset of the inputs
        parameters and a subsequent post on the edit page with the remaining
        parameters. However, the django client doesn't keep the context state
        in the same way as the browser. For now, ability to get the edit page
        is all that will be tested.
        """
        monkeypatch.setattr(
            f"webapp.apps.projects.{self.app_name}.views.Compute", self.mockcompute
        )
        monkeypatch.setattr("webapp.apps.core.views.Compute", self.mockcompute)

        self.login_client(client, profile.user, password)
        resp = client.post(reverse(self.title), data=self.inputs_ok())
        assert resp.status_code == 302  # redirect
        idx = resp.url[:-1].rfind("/")
        slug = resp.url[(idx + 1) : -1]
        outputs_url = resp.url
        assert outputs_url == f"{reverse(self.title)}{slug}/"

        # test get ouputs page
        resp = client.get(outputs_url)
        assert resp.status_code == 200

        # test get edit page
        edit_resp = client.get(f"{outputs_url}/edit")
        assert edit_resp.status_code == 200

    def test_run_reporting(self, monkeypatch, client, password, profile):
        """
        Tests:
        - post run
        """
        monkeypatch.setattr(
            f"webapp.apps.projects.{self.app_name}.views.Compute", self.mockcompute
        )
        monkeypatch.setattr("webapp.apps.core.views.Compute", self.mockcompute)

        self.login_client(client, profile.user, password)
        resp = client.post(reverse(self.title), data=self.inputs_ok())
        assert resp.status_code == 302  # redirect
        idx = resp.url[:-1].rfind("/")
        slug = resp.url[(idx + 1) : -1]
        assert resp.url == f"{reverse(self.title)}{slug}/"

        # test get ouputs page
        resp = client.get(resp.url)
        assert resp.status_code == 200

        output = self.RunModel.objects.get(pk=slug)
        assert output.profile
        assert output.project
        assert output.project.server_cost
        assert output.project.run_cost(output.run_time, adjust=True) > 0
        assert output.run_time > 0

        if self.provided_free:
            assert output.sponsor is not None

    def test_post_wo_login(self, monkeypatch, client):
        """
        Test post without logged-in user:
        - returns 302 status and redirects to login page on non-sponsored model.
        - the post kicks off a run on a sponsored model.
        """
        monkeypatch.setattr(
            f"webapp.apps.projects.{self.app_name}.views.Compute", self.mockcompute
        )
        monkeypatch.setattr("webapp.apps.core.views.Compute", self.mockcompute)

        resp = client.post(reverse(self.title), data=self.inputs_ok())
        if self.provided_free:
            assert resp.status_code == 302
            idx = resp.url[:-1].rfind("/")
            slug = resp.url[(idx + 1) : -1]
            assert resp.url == f"{reverse(self.title)}{slug}/"
        else:
            assert resp.status_code == 302
            assert resp.url == f"/users/login/?next={reverse(self.title)}"

    def login_client(self, client, user, password):
        """
        Helper method to login client
        """
        success = client.login(username=user.username, password=password)
        assert success
        return success

    @property
    def provided_free(self):
        if not hasattr(self, "project"):
            self.project = Project.objects.get(name=self.title)
        return self.project.sponsor is not None

    def inputs_ok(self):
        return {"has_errors": False}

    def outputs_ok(self):
        raise NotImplementedError()
