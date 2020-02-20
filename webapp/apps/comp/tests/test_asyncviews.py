import datetime
import os
import json
import uuid

import pytest
import requests_mock

from django.contrib import auth
from django.urls import reverse
from django.test import Client
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from rest_framework.response import Response

from webapp.apps.billing.models import UsageRecord
from webapp.apps.users.models import Project, Profile, create_profile_from_user

from webapp.apps.comp.models import Inputs, Simulation, PendingPermission, ANON_BEFORE
from webapp.apps.comp.ioutils import get_ioutils
from .compute import MockCompute, MockComputeWorkerFailure
from .utils import read_outputs, _submit_inputs, _submit_sim, _shuffled_sims

User = auth.get_user_model()


def login_client(client, user, password):
    """
    Helper function to login client. Calling logout
    ensures that previous credentials are cleared out.
    """
    client.logout()
    success = client.login(username=user.username, password=password)
    assert success
    return success


def set_auth_token(api_client: APIClient, user: User):
    """
    Set user's authentication credentials on the api_client object.
    Logout ensures that all credentials are cleared prior to logging
    in the new user.
    """
    api_client.logout()
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {user.auth_token.key}")


class CoreTestMixin:
    @property
    def project(self):
        if getattr(self, "_project", None) is None:
            self._project = Project.objects.get(
                owner__user__username__iexact=self.owner, title__iexact=self.title
            )
        return self._project


class ResponseStatusException(Exception):
    def __init__(self, exp_status, act_resp, stage):
        self.exp_status = exp_status
        self.act_resp = act_resp
        self.act_status = act_resp.status_code
        self.stage = stage
        super().__init__(
            f"{stage}: expected {exp_status}, got {self.act_status}\n\n{getattr(self.act_resp, 'data', None)}"
        )


def assert_status(exp_status, act_resp, stage):
    if exp_status != act_resp.status_code:
        raise ResponseStatusException(exp_status, act_resp, stage)


class RunMockModel(CoreTestMixin):
    def __init__(
        self,
        owner: str,
        title: str,
        defaults: dict,
        inputs: dict,
        errors_warnings: dict,
        client: Client,
        api_client: APIClient,
        worker_url: str,
        comp_api_user: User,
        monkeypatch,
        mockcompute: MockCompute,
        test_lower: bool,
    ):
        self.owner = owner
        self.title = title
        self.defaults = defaults
        self.inputs = inputs
        self.errors_warnings = errors_warnings
        self.client = client
        self.api_client = api_client
        self.worker_url = worker_url
        self.comp_api_user = comp_api_user
        self.monkeypatch = monkeypatch
        self.mockcompute = mockcompute

        if test_lower:
            self.title = self.title.lower()
            self.owner = self.owner.lower()

    def run(self):
        defaults_resp_data = {"status": "SUCCESS", **self.defaults}
        adj = self.inputs
        adj_job_id = str(uuid.uuid4())
        adj_resp_data = {"job_id": adj_job_id, "qlength": 1}
        adj_callback_data = {
            "status": "SUCCESS",
            "job_id": adj_job_id,
            **{"errors_warnings": self.errors_warnings},
        }
        with requests_mock.Mocker(real_http=True) as mock:
            init_resp = self.post_adjustment(
                mock, defaults_resp_data, adj_resp_data, adj
            )
            model_pk = init_resp.data["sim"]["model_pk"]
            sim = Simulation.objects.get(
                project__title__iexact=self.title,
                project__owner__user__username__iexact=self.owner,
                model_pk=model_pk,
            )
            self.sim_owner = sim.owner
            self.poll_adjustment(mock, model_pk)
            self.put_adjustment(adj_callback_data)
            inputs = self.check_adjustment_finished(model_pk)
            self.poll_simulation(inputs)

        model_pk = inputs.sim.model_pk
        self.check_simulation_finished(model_pk)

        # test get inputs from model_pk
        self.view_inputs_from_model_pk(model_pk)

        self.set_sim_description(model_pk)

        self.get_paths(model_pk)

    def post_adjustment(
        self,
        mock: requests_mock.Mocker,
        defaults_resp_data: dict,
        adj_resp_data: dict,
        adj: dict,
    ) -> Response:
        mock.register_uri(
            "POST",
            f"{self.worker_url}{self.owner}/{self.title}/inputs",
            text=json.dumps(defaults_resp_data),
        )
        mock.register_uri(
            "POST",
            f"{self.worker_url}{self.owner}/{self.title}/parse",
            text=json.dumps(adj_resp_data),
        )

        init_resp = self.api_client.post(
            f"/{self.owner}/{self.title}/api/v1/", data=adj, format="json"
        )
        assert_status(201, init_resp, "post_adjustment")
        return init_resp

    def poll_adjustment(self, mock: requests_mock.Mocker, model_pk: int):
        self.client.force_login(self.sim_owner.user)
        self.api_client.force_login(self.sim_owner.user)
        get_resp_pend = self.api_client.get(
            f"/{self.owner}/{self.title}/api/v1/{model_pk}/edit/"
        )
        assert_status(200, get_resp_pend, "poll_adjustment")
        assert get_resp_pend.data["status"] == "PENDING"

        edit_inputs_resp = self.client.get(
            f"/{self.owner}/{self.title}/{model_pk}/edit/"
        )
        assert_status(200, edit_inputs_resp, "poll_adjustment")

    def put_adjustment(self, adj_callback_data: dict) -> Response:
        set_auth_token(self.api_client, self.comp_api_user.user)
        self.mockcompute.client = self.api_client
        self.monkeypatch.setattr("webapp.apps.comp.views.api.Compute", self.mockcompute)
        put_adj_resp = self.api_client.put(
            f"/inputs/api/", data=adj_callback_data, format="json"
        )
        assert_status(200, put_adj_resp, "put_adjustment")
        return put_adj_resp

    def check_adjustment_finished(self, model_pk: str) -> Inputs:
        self.client.force_login(self.sim_owner.user)
        self.api_client.force_login(self.sim_owner.user)
        get_resp_succ = self.api_client.get(
            f"/{self.owner}/{self.title}/api/v1/{model_pk}/edit/"
        )
        assert_status(200, get_resp_succ, "check_adjustment_finished")
        assert get_resp_succ.data["status"] == "SUCCESS"
        assert get_resp_succ.data["sim"]["model_pk"]

        model_pk = get_resp_succ.data["sim"]["model_pk"]
        inputs = Inputs.objects.get(project=self.project, sim__model_pk=model_pk)
        assert inputs.sim.model_pk == model_pk
        assert inputs.sim.status == "PENDING"
        return inputs

    def poll_simulation(self, inputs: Inputs):
        model_pk = inputs.sim.model_pk
        self.mockcompute.sim = inputs.sim
        get_resp_pend = self.api_client.get(
            f"/{self.owner}/{self.title}/api/v1/{model_pk}/"
        )
        assert_status(202, get_resp_pend, "poll_simulation")

    def check_simulation_finished(self, model_pk: int):
        self.client.force_login(self.sim_owner.user)
        self.api_client.force_login(self.sim_owner.user)

        get_resp_succ = self.api_client.get(
            f"/{self.owner}/{self.title}/api/v1/{model_pk}/"
        )
        assert_status(200, get_resp_succ, "check_simulation_finished")
        model_pk = get_resp_succ.data["model_pk"]
        self.sim = Simulation.objects.get(project=self.project, model_pk=model_pk)
        assert self.sim.status == "SUCCESS"
        assert self.sim.outputs
        assert self.sim.traceback is None

    def view_inputs_from_model_pk(self, model_pk: int):
        get_resp_inputs = self.api_client.get(
            f"/{self.owner}/{self.title}/api/v1/{model_pk}/edit/"
        )
        assert_status(200, get_resp_inputs, "view_inputs_from_model_pk")
        data = get_resp_inputs.data
        assert "adjustment" in data
        assert data["sim"]["model_pk"] == model_pk

        edit_page = self.client.get(f"/{self.owner}/{self.title}/{model_pk}/edit/")
        assert_status(200, edit_page, "view_inputs_from_model_pk")

    def set_sim_description(self, model_pk: int):
        sim = Simulation.objects.get(
            project__owner__user__username__iexact=self.owner,
            project__title__iexact=self.title,
            model_pk=model_pk,
        )
        set_auth_token(self.api_client, sim.owner.user)
        get_sim_resp = self.api_client.get(
            f"/{self.owner}/{self.title}/api/v1/{model_pk}/remote/"
        )
        assert_status(200, get_sim_resp, "set_sim_description")
        data = get_sim_resp.data

        assert data["title"] == sim.title == "Untitled Simulation"
        assert data["owner"] == str(sim.owner)
        assert sim.parent_sim == None

        put_desc_resp = self.api_client.put(
            f"/{self.owner}/{self.title}/api/v1/{model_pk}/", data={"title": "My sim"}
        )
        assert_status(200, put_desc_resp, "set_sim_description")
        sim = Simulation.objects.get(
            project__owner__user__username__iexact=self.owner,
            project__title__iexact=self.title,
            model_pk=model_pk,
        )
        assert sim.title == "My sim"
        assert str(sim.owner)
        assert sim.parent_sim == None

    def get_paths(self, model_pk: int):
        def fetch_sims(exp_resp: int):
            api_paths = [
                f"/{self.owner}/{self.title}/api/v1/{model_pk}/remote/",
                f"/{self.owner}/{self.title}/api/v1/{model_pk}/",
                f"/{self.owner}/{self.title}/api/v1/{model_pk}/edit/",
            ]
            paths = [
                f"/{self.owner}/{self.title}/{model_pk}/",
                f"/{self.owner}/{self.title}/{model_pk}/edit/",
            ]
            for path in api_paths:
                resp = self.api_client.get(path)
                assert_status(exp_resp, resp, f"auth: {path}")
            for path in paths:
                resp = self.client.get(path)
                assert_status(exp_resp, resp, f"auth: {path}")

        # test with public sim
        self.sim.is_public = True
        self.sim.save()
        set_auth_token(self.api_client, self.sim_owner.user)
        self.client.force_login(self.sim_owner.user)
        fetch_sims(200)

        self.api_client.logout()
        self.client.logout()
        fetch_sims(200)

        # test with private sim
        self.sim.is_public = False
        self.sim.save()
        set_auth_token(self.api_client, self.sim.owner.user)
        self.client.force_login(self.sim_owner.user)

        fetch_sims(200)

        self.api_client.logout()
        self.client.logout()
        fetch_sims(403)


@pytest.fixture
def sponsored_matchups(db):
    sponsor = Profile.objects.get(user__username="sponsor")
    matchups = Project.objects.get(title="Matchups", owner__user__username="hdoupe")
    matchups.sponsor = sponsor
    matchups.save()


@pytest.mark.usefixtures("sponsored_matchups")
@pytest.mark.django_db
class TestAsyncAPI(CoreTestMixin):
    class MatchupsMockCompute(MockCompute):
        outputs = read_outputs("Matchups_v1")

    owner = "hdoupe"
    title = "Matchups"
    mockcompute = MatchupsMockCompute

    def inputs_ok(self):
        return {
            "meta_parameters": {"use_full_data": False},
            "adjustment": {"matchup": {"pitcher": "Max Scherzer"}},
        }

    def inputs_bad(self):
        return {
            "meta_parameters": {"use_full_data": True},
            "adjustment": {"matchup": {"pitcher": "not a pitcher"}},
        }

    def defaults(self):
        return {
            "meta_parameters": {
                "use_full_data": {
                    "title": "Use Full Data",
                    "description": "Flag that determines whether Matchups uses the 10 year data set or the 2018 data set.",
                    "type": "bool",
                    "value": True,
                    "validators": {"choice": {"choices": [True, False]}},
                }
            },
            "model_parameters": {"matchup": {"pitcher": {"title": "Pitcher"}}},
        }

    def errors_warnings(self):
        return {"matchup": {"errors": {}, "warnings": {}}}

    def test_get_inputs(self, api_client, worker_url):
        defaults = self.defaults()
        resp_data = {"status": "SUCCESS", **defaults}
        with requests_mock.Mocker() as mock:
            mock.register_uri(
                "POST",
                f"{worker_url}{self.owner}/{self.title}/inputs",
                text=json.dumps(resp_data),
            )
            resp = api_client.get(f"/{self.owner}/{self.title}/api/v1/inputs/")
            assert resp.status_code == 200

            ioutils = get_ioutils(self.project)
            exp = ioutils.displayer.package_defaults()
            assert exp == resp.data

    @pytest.mark.parametrize("use_api", [True, False])
    def test_new_sim(self, use_api, client, api_client, profile, worker_url):
        resp = client.get(f"/{self.owner}/{self.title}/")
        assert_status(200, resp, "test_new_sim")

        new_resp = client.get(f"/{self.owner}/{self.title}/new/")
        assert_status(200, new_resp, "test_new_sim")

        api_client.force_login(profile.user)
        client.force_login(profile.user)
        if use_api:
            auth_resp = api_client.post(f"/{self.owner}/{self.title}/api/v1/new/")
            assert_status(201, auth_resp, "test_new_sim_api")
            sim_url = auth_resp.data["sim"]["gui_url"]
        else:
            auth_resp = client.get(f"/{self.owner}/{self.title}/new/")
            assert_status(302, auth_resp, "test_new_sim_gui")
            sim_url = auth_resp.url

        sim_resp = client.get(sim_url)
        assert_status(200, sim_resp, sim_url)

        model_pk = int(sim_url.split("/")[3])

        sim = Simulation.objects.get(
            project__title=self.title,
            project__owner__user__username=self.owner,
            model_pk=model_pk,
        )

        assert sim.status == "STARTED"
        assert sim.inputs.status == "STARTED"

        api_client.logout()
        anon_resp = api_client.post(
            sim.get_absolute_api_url(),
            data={"adjustment": {}, "meta_parameters": {}},
            format="json",
        )
        assert_status(403, anon_resp, "test_new_sim_anon")

        u = User.objects.get(username="hdoupe")
        set_auth_token(api_client, u)
        anon_resp = api_client.post(
            sim.get_absolute_api_url(),
            data={"adjustment": {}, "meta_parameters": {}},
            format="json",
        )
        assert_status(403, anon_resp, "test_new_sim_oth_user")

        defaults = self.defaults()
        inputs_resp_data = {"status": "SUCCESS", **defaults}
        adj_resp_data = {"job_id": str(uuid.uuid4()), "qlength": 1}
        with requests_mock.Mocker() as mock:
            mock.register_uri(
                "POST",
                f"{worker_url}{self.owner}/{self.title}/inputs",
                text=json.dumps(inputs_resp_data),
            )
            mock.register_uri(
                "POST",
                f"{worker_url}{self.owner}/{self.title}/parse",
                text=json.dumps(adj_resp_data),
            )
            api_client.force_login(sim.owner.user)
            resp = api_client.get(sim.inputs.get_absolute_api_url())
            assert_status(200, resp, "test_new_sim_inputs")
            resp = api_client.get(sim.get_absolute_api_url())
            assert_status(200, resp, "test_new_sim_outputs")

            set_auth_token(api_client, profile.user)
            anon_resp = api_client.post(
                sim.get_absolute_api_url(),
                data={"adjustment": {}, "meta_parameters": {}},
                format="json",
            )
            assert_status(201, anon_resp, "test_new_sim_owner")

    def test_post_inputs(self, api_client, worker_url):
        defaults = self.defaults()
        resp_data = {"status": "SUCCESS", **defaults}
        meta_params = {"meta_parameters": self.inputs_ok()["meta_parameters"]}
        with requests_mock.Mocker() as mock:
            print("mocking", f"{worker_url}{self.owner}/{self.title}/inputs")
            mock.register_uri(
                "POST",
                f"{worker_url}{self.owner}/{self.title}/inputs",
                text=json.dumps(resp_data),
            )
            resp = api_client.post(
                f"/{self.owner}/{self.title}/api/v1/inputs/",
                data=meta_params,
                format="json",
            )
            assert resp.status_code == 200

            ioutils = get_ioutils(self.project)
            ioutils.displayer.meta_parameters.update(meta_params["meta_parameters"])
            exp = ioutils.displayer.package_defaults()
            assert exp == resp.data

    @pytest.mark.parametrize("test_lower", [False, True])
    def test_runmodel(
        self,
        monkeypatch,
        client,
        api_client,
        profile,
        worker_url,
        comp_api_user,
        test_lower,
    ):
        """
        Test lifetime of submitting a model.
        """
        set_auth_token(api_client, profile.user)

        rmm = RunMockModel(
            owner=self.owner,
            title=self.title,
            defaults=self.defaults(),
            inputs=self.inputs_ok(),
            errors_warnings=self.errors_warnings(),
            client=client,
            api_client=api_client,
            worker_url=worker_url,
            comp_api_user=comp_api_user,
            monkeypatch=monkeypatch,
            mockcompute=self.mockcompute,
            test_lower=test_lower,
        )
        rmm.run()

    def test_perms(
        self,
        monkeypatch,
        client,
        api_client,
        profile,
        profile_w_mockcustomer,
        worker_url,
        comp_api_user,
    ):
        """
        Test unable to post anon params.
        """
        kwargs = dict(
            owner=self.owner,
            title=self.title,
            defaults=self.defaults(),
            inputs=self.inputs_ok(),
            errors_warnings=self.errors_warnings(),
            client=client,
            api_client=api_client,
            worker_url=worker_url,
            comp_api_user=comp_api_user,
            monkeypatch=monkeypatch,
            mockcompute=self.mockcompute,
            test_lower=False,
        )
        rmm = RunMockModel(**kwargs)
        with pytest.raises(ResponseStatusException) as excinfo:
            rmm.run()
        assert excinfo.value.stage == "post_adjustment"
        assert excinfo.value.exp_status == 201
        assert excinfo.value.act_status == 403

        proj = Project.objects.get(
            title__iexact=self.title, owner__user__username__iexact=self.owner
        )
        proj.sponsor = None
        proj.save()

        if getattr(profile.user, "customer", None) is None:
            set_auth_token(api_client, profile_w_mockcustomer.user)
        else:
            set_auth_token(api_client, profile.user)
        rmm = RunMockModel(**kwargs)
        rmm.run()

        customer = getattr(profile.user, "customer", None)
        try:
            profile.customer = None
            profile.save()
            set_auth_token(api_client, profile.user)
            rmm = RunMockModel(**kwargs)
            with pytest.raises(ResponseStatusException) as excinfo:
                rmm.run()
            assert excinfo.value.stage == "post_adjustment"
            assert excinfo.value.exp_status == 201
            assert excinfo.value.act_status == 403
        finally:
            profile.customer = customer
            profile.save()

    @pytest.mark.parametrize("test_lower", [False, True])
    def test_fork(
        self,
        monkeypatch,
        client,
        api_client,
        profile,
        worker_url,
        comp_api_user,
        test_lower,
    ):
        """
        Test creating and forking a sim.
        """
        set_auth_token(api_client, profile.user)

        rmm = RunMockModel(
            owner=self.owner,
            title=self.title,
            defaults=self.defaults(),
            inputs=self.inputs_ok(),
            errors_warnings=self.errors_warnings(),
            client=client,
            api_client=api_client,
            worker_url=worker_url,
            comp_api_user=comp_api_user,
            monkeypatch=monkeypatch,
            mockcompute=self.mockcompute,
            test_lower=test_lower,
        )
        rmm.run()

        set_auth_token(api_client, profile.user)
        resp = api_client.post(
            f"/{self.owner}/{self.title}/api/v1/{rmm.sim.model_pk}/fork/"
        )
        assert resp.status_code == 201

        u = User.objects.get(username="modeler")
        assert profile.user != u
        set_auth_token(api_client, u)
        rmm.sim.is_public = True
        rmm.sim.save()
        resp = api_client.post(
            f"/{self.owner}/{self.title}/api/v1/{rmm.sim.model_pk}/fork/"
        )
        assert resp.status_code == 201

        api_client.logout()
        resp = api_client.post(
            f"/{self.owner}/{self.title}/api/v1/{rmm.sim.model_pk}/fork/"
        )
        assert resp.status_code == 403

        set_auth_token(api_client, profile.user)
        rmm.sim.status = "PENDING"
        rmm.sim.save()
        resp = api_client.post(
            f"/{self.owner}/{self.title}/api/v1/{rmm.sim.model_pk}/fork/"
        )
        assert resp.status_code == 400
        assert resp.data["fork"]


def test_placeholder_page(db, client):
    title = "Matchups"
    owner = "hdoupe"
    project = Project.objects.get(
        title__iexact=title, owner__user__username__iexact=owner
    )
    project.status = "pending"
    project.save()
    resp = client.get(f"/{owner}/{title}/")
    assert resp.status_code == 200
    project.status = "live"
    project.save()
    resp = client.get(f"/{owner}/{title}/")
    assert resp.status_code == 200


def test_outputs_api(db, api_client, profile, password):
    # Test auth errors return 401.
    anon_user = auth.get_user(api_client)
    assert not anon_user.is_authenticated
    assert api_client.put("/outputs/api/").status_code == 401
    api_client.login(username=profile.user.username, password=password)
    assert api_client.put("/outputs/api/").status_code == 401

    # Test data errors return 400
    user = User.objects.get(username="comp-api-user")
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {user.auth_token.key}")
    assert (
        api_client.put("/outputs/api/", data={"bad": "data"}, format="json").status_code
        == 400
    )


def test_anon_get_create_api(db, api_client):
    anon_user = auth.get_user(api_client)
    assert not anon_user.is_authenticated

    resp = api_client.get("/hdoupe/Matchups/api/v1/")
    assert resp.status_code == 405

    resp = api_client.post(
        "/hdoupe/Matchups/api/v1/",
        data={"adjustment": {}, "meta_parameters": {}},
        format="json",
    )
    assert resp.status_code == 403


def test_v0_urls(
    db, sponsored_matchups, client, api_client, get_inputs, meta_param_dict
):
    """
    Test responses on v0 outputs.
    - public
    - private
    - title update
    """
    modeler = User.objects.get(username="hdoupe").profile
    inputs = _submit_inputs("Matchups", get_inputs, meta_param_dict, modeler)

    _, submit_sim = _submit_sim(inputs)
    sim = submit_sim.submit()
    sim.status = "SUCCESS"
    sim.is_public = True
    v0_outputs = json.loads(read_outputs("Matchups_v0"))
    sim.outputs = v0_outputs
    sim.save()

    assert sim.outputs_version() == "v0"

    # Test public responses.
    resp = client.get(f"/{sim.project.owner}/{sim.project.title}/{sim.model_pk}/")
    assert_status(302, resp, "v0-redirect")
    resp = client.get(f"/{sim.project.owner}/{sim.project.title}/{sim.model_pk}/v0/")
    assert_status(200, resp, "v0")
    resp = client.get(f"/{sim.project.owner}/{sim.project.title}/{sim.model_pk}/edit/")
    assert_status(200, resp, "v0-edit")
    resp = api_client.get(
        f"/{sim.project.owner}/{sim.project.title}/api/v1/{sim.model_pk}/"
    )
    assert_status(200, resp, "v0-api-get")
    resp = api_client.get(
        f"/{sim.project.owner}/{sim.project.title}/api/v1/{sim.model_pk}/edit/"
    )
    assert_status(200, resp, "v0-edit-api-get")

    # Test private responses.
    s = Simulation.objects.get(pk=sim.pk)
    s.is_public = False
    s.save()

    resp = client.get(f"/{sim.project.owner}/{sim.project.title}/{sim.model_pk}/")
    assert_status(403, resp, "v0-redirect")
    resp = client.get(f"/{sim.project.owner}/{sim.project.title}/{sim.model_pk}/v0/")
    assert_status(403, resp, "v0")
    resp = client.get(f"/{sim.project.owner}/{sim.project.title}/{sim.model_pk}/edit/")
    assert_status(403, resp, "v0-edit")
    resp = api_client.get(
        f"/{sim.project.owner}/{sim.project.title}/api/v1/{sim.model_pk}/"
    )
    assert_status(403, resp, "v0-api-get")

    api_client.force_login(sim.owner.user)
    client.force_login(sim.owner.user)
    resp = client.get(f"/{sim.project.owner}/{sim.project.title}/{sim.model_pk}/v0/")
    assert_status(200, resp, "v0-get-private")
    resp = api_client.get(
        f"/{sim.project.owner}/{sim.project.title}/api/v1/{sim.model_pk}/"
    )
    assert_status(200, resp, "v0-api-get")

    # Test update title and public/private status.
    resp = api_client.put(
        f"/{sim.project.owner}/{sim.project.title}/api/v1/{sim.model_pk}/",
        data={"title": "hello world"},
        format="json",
    )
    assert_status(200, resp, "v0-api-put")
    s = Simulation.objects.get(pk=sim.pk)
    assert s.title == "hello world"

    resp = api_client.put(
        f"/{sim.project.owner}/{sim.project.title}/api/v1/{sim.model_pk}/",
        data={"is_public": False},
        format="json",
    )
    assert_status(200, resp, "v0-api-change-access")
    s = Simulation.objects.get(pk=sim.pk)
    assert s.is_public == False


def test_add_author_flow(
    db, sponsored_matchups, client, api_client, get_inputs, meta_param_dict, profile
):
    """
    Test full add new author flow.
    """
    modeler = User.objects.get(username="hdoupe").profile
    inputs = _submit_inputs("Matchups", get_inputs, meta_param_dict, modeler)

    _, submit_sim = _submit_sim(inputs)
    sim = submit_sim.submit()
    sim.status = "SUCCESS"
    sim.is_public = True
    sim.save()

    assert sim.authors.all().count() == 1 and sim.authors.get(pk=sim.owner.pk)

    # Permission denied on unauthed user
    resp = api_client.put(
        f"{sim.get_absolute_api_url()}authors/",
        data={"authors": [profile.user.username]},
        format="json",
    )
    assert_status(403, resp, "denied_authors")

    # Permission denied if user is not owner of sim.
    api_client.force_login(profile.user)
    resp = api_client.put(
        f"{sim.get_absolute_api_url()}authors/",
        data={"authors": [profile.user.username]},
        format="json",
    )
    assert_status(403, resp, "denied_authors")

    # Successful update
    api_client.force_login(modeler.user)
    resp = api_client.put(
        f"{sim.get_absolute_api_url()}authors/",
        data={"authors": [profile.user.username]},
        format="json",
    )
    assert_status(200, resp, "success_authors")

    sim = Simulation.objects.get(pk=sim.pk)
    assert sim.authors.all().count() == 1 and sim.authors.get(pk=sim.owner.pk)
    assert sim.pending_permissions.all().count() == 1 and sim.pending_permissions.all().get(
        profile=profile
    )
    pp = sim.pending_permissions.first()

    # Test user redirected to login if not authed.
    resp = client.get(pp.get_absolute_url())
    assert_status(302, resp, "pending_redirect_to_login")
    assert resp.url == f"/users/login/?next={pp.get_absolute_url()}"

    # Login profile, go to permission confirmation page.
    client.force_login(user=profile.user)
    resp = client.get(pp.get_absolute_url())
    assert_status(200, resp, "get_permissions_pending")
    assert "comp/permissions/confirm.html" in [t.name for t in resp.templates]
    # GET link for granting permission.
    resp = client.get(pp.get_absolute_grant_url())
    assert_status(302, resp, "grant_permissions")
    assert resp.url == sim.get_absolute_url()

    sim = Simulation.objects.get(pk=sim.pk)
    assert sim.authors.all().count() == 2
    assert sim.authors.filter(pk__in=[modeler.pk, profile.pk]).count() == 2
    assert sim.pending_permissions.count() == 0


def test_add_authors_api(
    db, sponsored_matchups, client, api_client, get_inputs, meta_param_dict, profile
):
    """
    Test add authors api endpoints.
    """
    modeler = User.objects.get(username="hdoupe").profile
    inputs = _submit_inputs("Matchups", get_inputs, meta_param_dict, modeler)

    _, submit_sim = _submit_sim(inputs)
    sim = submit_sim.submit()
    sim.status = "SUCCESS"
    sim.is_public = True
    sim.save()

    assert sim.authors.all().count() == 1 and sim.authors.get(pk=sim.owner.pk)

    # first create a pending permission through the api
    api_client.force_login(modeler.user)
    resp = api_client.put(
        f"{sim.get_absolute_api_url()}authors/",
        data={"authors": [profile.user.username]},
        format="json",
    )
    assert_status(200, resp, "success_authors")

    # check that resubmit has no effect on non-expired permissions.
    init_pp = sim.pending_permissions.get(profile__pk=profile.pk)
    assert PendingPermission.objects.count() == 1

    resp = api_client.put(
        f"{sim.get_absolute_api_url()}authors/",
        data={"authors": [profile.user.username]},
        format="json",
    )
    assert_status(200, resp, "success_authors")

    # init_pp is still the only permission that we have.
    assert PendingPermission.objects.count() == 1
    assert sim.pending_permissions.get(pk=init_pp.pk) == init_pp

    init_pp.expiration_date = init_pp.creation_date - datetime.timedelta(days=3)
    init_pp.save()
    assert init_pp.is_expired() == True

    resp = api_client.put(
        f"{sim.get_absolute_api_url()}authors/",
        data={"authors": [profile.user.username]},
        format="json",
    )
    assert_status(200, resp, "success_authors")

    # Check that stale permission is removed and a new one is added.
    assert PendingPermission.objects.count() == 1
    assert PendingPermission.objects.filter(pk=init_pp.pk).count() == 0
    new_pp = sim.pending_permissions.get(profile__pk=profile.pk)
    assert new_pp.sim == sim


def test_delete_author(
    db, sponsored_matchups, client, api_client, get_inputs, meta_param_dict, profile
):
    """
    Test delete author from simulation.
    - owner cannot be deleted from author list.
    - check delete before permission approval.
    - check delete of existing author.
    - 404 on dne or unassociated author.
    - author can remove themselves as author.
    """
    modeler = User.objects.get(username="hdoupe").profile
    inputs = _submit_inputs("Matchups", get_inputs, meta_param_dict, modeler)

    _, submit_sim = _submit_sim(inputs)
    sim = submit_sim.submit()
    sim.status = "SUCCESS"
    sim.is_public = True
    sim.save()

    assert sim.authors.all().count() == 1 and sim.authors.get(pk=sim.owner.pk)

    # test not allowed to delete owner of simulation from authors.
    api_client.force_login(modeler.user)
    resp = api_client.delete(f"{sim.get_absolute_api_url()}authors/{sim.owner}/")
    assert_status(400, resp, "cannot_delete_sim_owner")
    sim = Simulation.objects.get(pk=sim.pk)
    assert sim.authors.all().count() == 1 and sim.authors.get(pk=sim.owner.pk)

    # first create a pending permission through the api.
    resp = api_client.put(
        f"{sim.get_absolute_api_url()}authors/",
        data={"authors": [profile.user.username]},
        format="json",
    )
    assert_status(200, resp, "success_authors")

    init_pp = sim.pending_permissions.get(profile__pk=profile.pk)

    # test delete author before they approve request.
    resp = api_client.delete(f"{sim.get_absolute_api_url()}authors/{profile}/")
    assert_status(204, resp, "delete_pending_author")
    assert PendingPermission.objects.filter(id=init_pp.id).count() == 0
    sim = Simulation.objects.get(pk=sim.pk)
    assert sim.authors.all().count() == 1 and sim.authors.get(pk=sim.owner.pk)

    # test delete author.
    api_client.force_login(modeler.user)
    resp = api_client.put(
        f"{sim.get_absolute_api_url()}authors/",
        data={"authors": [profile.user.username]},
        format="json",
    )
    assert_status(200, resp, "success_authors")

    new_pp = sim.pending_permissions.get(profile__pk=profile.pk)
    new_pp.add_author()
    assert sim.authors.all().count() == 2 and sim.authors.get(pk=profile.pk)

    resp = api_client.delete(f"{sim.get_absolute_api_url()}authors/{profile}/")
    assert_status(204, resp, "delete_pending_author")
    assert PendingPermission.objects.filter(id=init_pp.id).count() == 0
    sim = Simulation.objects.get(pk=sim.pk)
    assert sim.authors.all().count() == 1 and sim.authors.get(pk=sim.owner.pk)

    # test not found
    resp = api_client.delete(f"{sim.get_absolute_api_url()}authors/{profile}/")
    assert_status(404, resp, "delete_author_already_deleted")
    resp = api_client.delete(f"{sim.get_absolute_api_url()}authors/abcd/")
    assert_status(404, resp, "delete_author_profile_dne")

    # test unauth'ed user does not have access.
    api_client.logout()
    resp = api_client.delete(f"{sim.get_absolute_api_url()}authors/{profile}/")
    assert_status(403, resp, "delete_author_must_be_auth'ed")

    # test profile can remove themselves.
    api_client.force_login(modeler.user)
    resp = api_client.put(
        f"{sim.get_absolute_api_url()}authors/",
        data={"authors": [profile.user.username]},
        format="json",
    )
    assert_status(200, resp, "success_authors")

    api_client.force_login(profile.user)
    resp = api_client.delete(f"{sim.get_absolute_api_url()}authors/{profile}/")
    assert_status(204, resp, "author_can_deletle_themselves")

    # test must have write access or be removing oneself
    u = User.objects.create_user("danger", "danger@example.com", "heyhey2222")
    create_profile_from_user(u)
    danger = Profile.objects.get(user__username="danger")
    api_client.force_login(danger.user)
    resp = api_client.delete(f"{sim.get_absolute_api_url()}authors/{profile}/")
    assert_status(403, resp, "auth'ed user cannot delete authors")


def test_list_sim_api(db, api_client, profile, get_inputs, meta_param_dict):
    modeler = User.objects.get(username="modeler").profile
    sims, modeler_sims, tester_sims = _shuffled_sims(
        profile, get_inputs, meta_param_dict
    )
    # test can't access api/v1/sims if not authenticated.
    resp = api_client.get("/api/v1/sims")
    assert_status(403, resp, "unauthed_list_sims")
    resp = api_client.get("/api/v1/sims?ordering=project__title")
    assert_status(403, resp, "unauthed_list_sims")

    # test can't view others private simulations
    resp = api_client.get("/api/v1/sims/tester")
    assert_status(200, resp, "unauthed_list_profile_sims")
    assert len(resp.data["results"]) == 0

    # test only public sims are shown on profile page.
    tester_sims[1].is_public = True
    tester_sims[1].save()
    resp = api_client.get("/api/v1/sims/tester")
    assert_status(200, resp, "unauthed_list_profile_sims")
    assert len(resp.data["results"]) == 1
    assert resp.data["results"][0]["model_pk"] == tester_sims[1].model_pk

    # ensure anon_before is checked.
    tester_sims[1].creation_date = ANON_BEFORE - datetime.timedelta(days=2)
    tester_sims[1].is_public = True
    tester_sims[1].save()
    resp = api_client.get("/api/v1/sims/tester")
    assert_status(200, resp, "unauthed_list_profile_sims")
    assert len(resp.data["results"]) == 0

    # Check auth'ed user can view their own sims.
    api_client.force_login(profile.user)
    resp = api_client.get("/api/v1/sims")
    assert_status(200, resp, "authed_list_sims")
    print(sims[-1].owner)
    modelpks = {sim["model_pk"] for sim in resp.data["results"]}
    assert modelpks == set(sim.model_pk for sim in tester_sims)

    # Check auth'ed user can only view others public sims.
    modeler_sims[0].is_public = True
    modeler_sims[0].save()
    resp = api_client.get("/api/v1/sims/modeler")
    assert_status(200, resp, "unauthed_list_profile_sims")
    assert len(resp.data["results"]) == 1
    assert resp.data["results"][0]["model_pk"] == modeler_sims[0].model_pk
