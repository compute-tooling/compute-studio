import pytest

from django.contrib import auth

from webapp.apps.core.tests.compute import MockCompute

@pytest.mark.django_db
class CoreAbstractViewsTest():
    """
    Abstract test class to be used for efficient testing of modeling projects.
    The approach used here goes against conventional wisdom to use simple,
    stupid test code. This is done because there will be many types of models
    that share a "core" functionality. Re-writing and maintaining many copies
    of the same tests would be cumbersome, time-consuming, and error-prone.
    """
    app_name = 'core'
    post_data_ok = {}
    mockcompute = None
    RunModel = None

    def test_get(self, monkeypatch, client):
        """
        Test simple get returns 200 status
        """
        resp = client.get(f'/{self.app_name}/')
        assert resp.status_code == 200

    def test_logged_in(self, client, profile, password):
        """
        Test simple get returns AnonymousUser and login returns authenticated
        user
        """
        resp = client.get(f'/{self.app_name}/')
        assert resp.status_code == 200
        anon_user = auth.get_user(client)
        assert not anon_user.is_authenticated

        assert self.login_client(client, profile.user, password)
        resp = client.get(f'/{self.app_name}/')
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
        monkeypatch.setattr(f'webapp.apps.{self.app_name}.views.Compute',
                            self.mockcompute)
        monkeypatch.setattr('webapp.apps.core.views.Compute', self.mockcompute)

        self.login_client(client, profile.user, password)
        resp = client.post(f'/{self.app_name}/', data=self.inputs_ok())
        assert resp.status_code == 302 # redirect
        idx = resp.url[:-1].rfind('/')
        slug = resp.url[(idx + 1):-1]
        assert resp.url == f'/{self.app_name}/{slug}/'

        # test get ouputs page
        resp = client.get(resp.url)
        assert resp.status_code == 200

        # test ouptut download
        resp = client.get(f'/{self.app_name}/{slug}/download')
        assert resp.status_code == 200
        assert resp._headers['content-type'] == ('Content-Type',
                                                 'application/zip')

    def test_run_reporting(self, monkeypatch, client, password, profile):
        """
        Tests:
        """
        monkeypatch.setattr(f'webapp.apps.{self.app_name}.views.Compute',
                            self.mockcompute)
        monkeypatch.setattr('webapp.apps.core.views.Compute', self.mockcompute)

        self.login_client(client, profile.user, password)
        resp = client.post(f'/{self.app_name}/', data=self.inputs_ok())
        assert resp.status_code == 302 # redirect
        idx = resp.url[:-1].rfind('/')
        slug = resp.url[(idx + 1):-1]
        assert resp.url == f'/{self.app_name}/{slug}/'

        # test get ouputs page
        resp = client.get(resp.url)
        assert resp.status_code == 200

        output = self.RunModel.objects.get(pk=slug)
        assert output.profile
        assert output.project
        assert output.project.server_cost
        assert output.project.run_cost(output.run_time, adjust=True) > 0
        assert output.run_time > 0


    def test_post_wo_login_redirects_to_login(self, client):
        """
        Test post without logged-in user returns 302 status and redirects
        to login page
        """
        resp = client.post(f'/{self.app_name}/', data=self.inputs_ok())
        assert resp.status_code == 302
        assert resp.url == '/users/login/?next=/upload/'

    def login_client(self, client, user, password):
        """
        Helper method to login client
        """
        success = client.login(username=user.username, password=password)
        assert success
        return success

    def inputs_ok(self):
        raise NotImplementedError()

    def outputs_ok(self):
        raise NotImplementedError()