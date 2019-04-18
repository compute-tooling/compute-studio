import os
import json

import pytest

from django.contrib import auth
from django.urls import reverse

from webapp.apps.users.models import Project, Profile

from webapp.apps.comp.models import Simulation
from .compute import MockCompute


User = auth.get_user_model()


class CoreTestMixin:
    def login_client(self, client, user, password):
        """
        Helper function to login client
        """
        success = client.login(username=user.username, password=password)
        assert success
        return success

    @property
    def provided_free(self):
        raise NotImplementedError()

    def inputs_ok(self):
        return {"has_errors": False}

    def outputs_ok(self):
        raise NotImplementedError()

    @property
    def project(self):
        if getattr(self, "_project", None) is None:
            self._project = Project.objects.get(
                owner__user__username=self.owner, title=self.title
            )
        return self._project


@pytest.mark.django_db
class CoreAbstractViewsTest(CoreTestMixin):
    """
    Abstract test class to be used for efficient testing of modeling projects.
    The approach used here goes against conventional wisdom to use simple,
    stupid test code. This is done because there will be many types of models
    that share a "core" functionality. Re-writing and maintaining many copies
    of the same tests would be cumbersome, time-consuming, and error-prone.
    """

    title = "Core"
    post_data_ok = {}
    mockcompute = None

    def test_get(self, monkeypatch, client):
        """
        Test simple get returns 200 status
        """
        resp = client.get(self.project.app_url)
        assert resp.status_code == 200

    def test_logged_in(self, client, profile, password):
        """
        Test simple get returns AnonymousUser and login returns authenticated
        user
        """
        resp = client.get(self.project.app_url)
        assert resp.status_code == 200
        anon_user = auth.get_user(client)
        assert not anon_user.is_authenticated

        assert self.login_client(client, profile.user, password)
        resp = client.get(self.project.app_url)
        assert resp.status_code == 200
        user = auth.get_user(client)
        assert user.is_authenticated

    def test_post(self, monkeypatch, client, profile, password):
        """
        Tests:
        - post with logged-in user returns 302 redirect
        - test render results page returns 200
        - test download page returns 200 and zip file content
        - test logged out user can view outputs page
        """
        slug = self.post_data(monkeypatch, client, self.inputs_ok(), profile, password)

        # test ouptut download
        resp = client.get(f"{self.project.app_url}{slug}/")
        assert resp.status_code == 200

    def test_download_results(self, monkeypatch, client, profile, password):
        slug = self.post_data(monkeypatch, client, self.inputs_ok(), profile, password)
        resp = client.get(f"{self.project.app_url}{slug}/download/")
        assert resp.status_code == 200
        assert resp._headers["content-type"] == ("Content-Type", "application/zip")
        resp = client.get(f"{self.project.app_url}{slug}/download/?raw_json=True")
        assert resp.status_code == 200
        assert resp._headers["content-type"] == ("Content-Type", "text/plain")

    def test_edit_page(self, monkeypatch, client, profile, password):
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
        slug = self.post_data(monkeypatch, client, self.inputs_ok(), profile, password)
        # test get edit page
        edit_resp = client.get(f"{self.project.app_url}{slug}/edit/")
        assert edit_resp.status_code == 200

    def test_run_reporting(self, monkeypatch, client, profile, password):
        """
        Tests:
        - post run
        """
        slug = self.post_data(monkeypatch, client, self.inputs_ok(), profile, password)

        output = Simulation.objects.get(model_pk=slug, project=self.project)
        assert output.owner
        assert output.project
        assert output.project.server_cost
        assert output.project.run_cost(output.run_time, adjust=True) > 0
        assert output.run_time > 0

        if self.provided_free:
            assert output.sponsor is not None

    def test_post_wo_login(self, monkeypatch, client):
        """
        Test post without logged-in user:
        - returns 302 status and redirects to login page.
        """
        monkeypatch.setattr("webapp.apps.comp.views.Compute", self.mockcompute)

        resp = client.post(self.project.app_url, data=self.inputs_ok())
        assert resp.status_code == 302
        assert resp.url == f"/users/login/?next={self.project.app_url}"

    def test_post_wo_payment_info(self, monkeypatch, client):
        """
        Test post without logged-in user:
        - returns 302 status and redirects to update payment method on
          non-sponsored model.
        - the post kicks off a run on a sponsored model.
        """
        monkeypatch.setattr("webapp.apps.comp.views.Compute", self.mockcompute)

        u = User.objects.create_user(
            username="test-no-pmt",
            email="test-no-pmt@email.com",
            password="testtest2222",
        )
        prof = Profile.objects.create(user=u, is_active=True)
        assert self.login_client(client, u, "testtest2222")
        assert not hasattr(u, "customer")

        resp = client.post(self.project.app_url, data=self.inputs_ok())
        if self.provided_free:
            # kick off run
            assert resp.status_code == 302
            idx = resp.url[:-1].rfind("/")
            slug = resp.url[(idx + 1) : -1]
            assert resp.url == f"{self.project.app_url}{slug}/"
        else:
            assert resp.status_code == 302
            assert resp.url == f"/billing/update/?next={self.project.app_url}"

    def test_push_in_detail(self, monkeypatch, client, profile, password):
        """
        Tests:
        1. POST with logged-in user returns 302 redirect which means the sim
           was kicked off.
        2. Retrieve the simulation object and pass that to the mockcompute
           class as a class attribute. (I know it's hacky.)
        3. Do a POST to simulate an AJAX request from the loading page.
           MockPushCompute mocks the request to the celery workers with
           response indicating that the results are not ready, and pushes the
           outputs via a PUT on the /outputs/api endpoint. The OutputsView
           returns a 202 indicating that the results are not yet ready.
        4. Check to make sure that the PUT was successful.
        5. Do another AJAX like POST and make sure the outputs are found on the
           simulation object and a 200 is returned.
        """
        slug = self.post_data(monkeypatch, client, self.inputs_ok(), profile, password)

        # output should now be set!
        sim = Simulation.objects.get(project=self.project, model_pk=slug)
        assert sim.outputs["version"]
        assert sim.outputs["outputs"]
        assert sim.run_time
        assert sim.project.run_cost(sim.run_time, adjust=True) > 0

        sim_url = f"{self.project.app_url}{slug}/"
        resp = client.post(sim_url)
        assert resp.status_code == 200

    def test_sim_doesnt_exist_gives_404(self, db, client):
        """
        Test get sim results that don't exist throws a 404.
        """
        resp = client.get(f"{self.project.app_url}/100000/")
        assert resp.status_code == 404

    def post_data(self, monkeypatch, client, inputs, profile, password):
        self.mockcompute.client = client
        monkeypatch.setattr("webapp.apps.comp.views.Compute", self.mockcompute)

        self.login_client(client, profile.user, password)
        resp = client.post(self.project.app_url, data=inputs)
        assert resp.status_code == 302  # redirect
        idx = resp.url[:-1].rfind("/")
        slug = resp.url[(idx + 1) : -1]
        sim_url = resp.url
        assert sim_url == f"{self.project.app_url}{slug}/"

        # Pass the sim object to the Compute instance via a class attribute.
        sim = Simulation.objects.get(project=self.project, model_pk=slug)
        self.mockcompute.sim = sim

        # test get ouputs page
        resp = client.post(resp.url)
        # redirect since the outputs have only just been set.
        assert resp.status_code == 202

        return slug


def read_outputs(outputs_name):
    curr = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(curr, f"{outputs_name}.json"), "r") as f:
        outputs = f.read()
    return outputs


@pytest.fixture
def unsponsored_matchups(db):
    matchups = Project.objects.get(title="Matchups", owner__user__username="hdoupe")
    matchups.sponsor = None
    matchups.save()


@pytest.fixture
def sponsored_matchups(db):
    sponsor = Profile.objects.get(user__username="sponsor")
    matchups = Project.objects.get(title="Matchups", owner__user__username="hdoupe")
    matchups.sponsor = sponsor
    matchups.save()


@pytest.mark.usefixtures("sponsored_matchups")
class TestMatchupsV0Sponsored(CoreAbstractViewsTest):
    class MatchupsMockCompute(MockCompute):
        outputs = read_outputs("Matchups_v0")

    owner = "hdoupe"
    title = "Matchups"
    mockcompute = MatchupsMockCompute

    def inputs_ok(self):
        inputs = super().inputs_ok()
        upstream_inputs = {"pitcher": "Max Scherzer"}
        return dict(inputs, **upstream_inputs)

    def outputs_ok(self):
        return read_outputs("Matchups_1")

    @property
    def provided_free(self):
        return True


@pytest.mark.requires_stripe
@pytest.mark.usefixtures("unsponsored_matchups")
class TestMatchupsV1(CoreAbstractViewsTest):
    class MatchupsMockCompute(MockCompute):
        outputs = read_outputs("Matchups_v1")

    owner = "hdoupe"
    title = "Matchups"
    mockcompute = MatchupsMockCompute

    def inputs_ok(self):
        inputs = super().inputs_ok()
        upstream_inputs = {"pitcher": "Max Scherzer"}
        return dict(inputs, **upstream_inputs)

    def outputs_ok(self):
        return read_outputs("Matchups_1")

    @property
    def provided_free(self):
        return False


@pytest.mark.usefixtures("sponsored_matchups")
class TestMatchupsV1Sponsored(CoreAbstractViewsTest):
    class MatchupsMockCompute(MockCompute):
        outputs = read_outputs("Matchups_v1")

    owner = "hdoupe"
    title = "Matchups"
    mockcompute = MatchupsMockCompute

    def inputs_ok(self):
        inputs = super().inputs_ok()
        upstream_inputs = {"pitcher": "Max Scherzer"}
        return dict(inputs, **upstream_inputs)

    def outputs_ok(self):
        return read_outputs("Matchups_1")

    @property
    def provided_free(self):
        return True


def test_404_owner_title_view(db, client):
    resp = client.get("/hello/world/")
    assert resp.status_code == 404


def test_placeholder_page(db, client):
    title = "Matchups"
    owner = "hdoupe"
    project = Project.objects.get(title=title, owner__user__username=owner)
    project.status = "pending"
    project.save()
    resp = client.get(f"/{owner}/{title}/")
    assert resp.status_code == 200
    assert "comp/model_placeholder.html" in [t.name for t in resp.templates]
    project.status = "live"
    project.save()
    resp = client.get(f"/{owner}/{title}/")
    assert resp.status_code == 200
    assert "comp/inputs_form.html" in [t.name for t in resp.templates]


def test_outputs_api(db, client, profile, password):
    # Test auth errors return 401.
    anon_user = auth.get_user(client)
    assert not anon_user.is_authenticated
    assert client.put("/outputs/api/").status_code == 401
    client.login(username=profile.user.username, password=password)
    assert client.put("/outputs/api/").status_code == 401

    # Test data errors return 400
    user = User.objects.get(username="comp-api-user")
    client.login(username=user.username, password="heyhey2222")
    assert (
        client.put(
            "/outputs/api/", data={"bad": "data"}, content_type="application/json"
        ).status_code
        == 400
    )
