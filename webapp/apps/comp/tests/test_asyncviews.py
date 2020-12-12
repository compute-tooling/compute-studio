import datetime
import os
import json
import time
import uuid

import pytest
import requests_mock

from django.contrib import auth
from django.urls import reverse
from django.test import Client
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from rest_framework.response import Response

from webapp.settings import FREE_PRIVATE_SIMS
from webapp.apps.billing.tests.utils import gen_blank_customer
from webapp.apps.users.models import (
    Project,
    Profile,
    EmbedApproval,
    Deployment,
    Tag,
    create_profile_from_user,
)
from webapp.apps.users.tests.utils import gen_collabs, replace_owner
from webapp.apps.comp.models import (
    Inputs,
    Simulation,
    PendingPermission,
    ANON_BEFORE,
)
from webapp.apps.comp.ioutils import get_ioutils
from webapp.apps.comp.exceptions import PrivateSimException
from .compute import MockCompute
from .utils import (
    read_outputs,
    _submit_inputs,
    _submit_sim,
    _shuffled_sims,
)

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
            self._project = Project.objects.get(title__iexact=self.title)
        return self._project

    @property
    def owner(self):
        return str(self.project.owner)

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


class ResponseStatusException(Exception):
    def __init__(self, exp_status, act_resp, stage):
        self.exp_status = exp_status
        self.act_resp = act_resp
        self.act_status = act_resp.status_code
        self.stage = stage
        super().__init__(f"{stage}: expected {exp_status}, got {self.act_status}")


def assert_status(exp_status, act_resp, stage):
    if isinstance(exp_status, list) and act_resp.status_code not in exp_status:
        raise ResponseStatusException(exp_status, act_resp, stage)
    elif not isinstance(exp_status, list) and exp_status != act_resp.status_code:
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
        comp_api_user: User,
        monkeypatch,
        mockcompute: MockCompute,
        test_lower: bool,
    ):
        self.title = title
        self.defaults = defaults
        self.inputs = inputs
        self.errors_warnings = errors_warnings
        self.client = client
        self.api_client = api_client
        self.comp_api_user = comp_api_user
        self.monkeypatch = monkeypatch
        self.mockcompute = mockcompute

        if test_lower:
            self.title = self.title.lower()

    def run(self):
        defaults_resp_data = {"status": "SUCCESS", **self.defaults}
        adj = self.inputs
        adj_job_id = str(uuid.uuid4())
        adj_resp_data = {"task_id": adj_job_id}
        adj_callback_data = {
            "status": "SUCCESS",
            "task_id": adj_job_id,
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
            f"{self.project.cluster.url}/{self.project}/",
            json=lambda request, context: {
                "defaults": defaults_resp_data,
                "parse": adj_resp_data,
                "version": {"status": "SUCCESS", "version": "v1"},
            }[request.json()["task_name"]],
        )
        init_resp = self.api_client.post(
            f"/{self.project}/api/v1/", data=adj, format="json"
        )
        assert_status(201, init_resp, "post_adjustment")
        return init_resp

    def poll_adjustment(self, mock: requests_mock.Mocker, model_pk: int):
        self.client.force_login(self.sim_owner.user)
        self.api_client.force_login(self.sim_owner.user)
        get_resp_pend = self.api_client.get(f"/{self.project}/api/v1/{model_pk}/edit/")
        assert_status(200, get_resp_pend, "poll_adjustment")
        assert get_resp_pend.data["status"] == "PENDING"

        edit_inputs_resp = self.client.get(f"/{self.project}/{model_pk}/edit/")
        assert_status(200, edit_inputs_resp, "poll_adjustment")

    def put_adjustment(self, adj_callback_data: dict) -> Response:
        # Test permissions on /inputs/api/ endpoint.
        self.api_client.logout()
        not_authed = self.api_client.put(
            f"/inputs/api/", data=adj_callback_data, format="json"
        )
        assert_status(401, not_authed, "put_adjustment_not_authed")

        self.api_client.force_login(User.objects.get(username="hdoupe"))
        not_authed = self.api_client.put(
            f"/inputs/api/", data=adj_callback_data, format="json"
        )
        assert_status(401, not_authed, "put_adjustment_no_perms")
        self.api_client.logout()

        self.mockcompute.client = self.api_client
        self.monkeypatch.setattr("webapp.apps.comp.views.api.Compute", self.mockcompute)
        put_adj_resp = self.api_client.put(
            f"/inputs/api/",
            data=adj_callback_data,
            format="json",
            **self.project.cluster.headers(),
        )
        assert_status(200, put_adj_resp, "put_adjustment")
        return put_adj_resp

    def check_adjustment_finished(self, model_pk: str) -> Inputs:
        self.client.force_login(self.sim_owner.user)
        self.api_client.force_login(self.sim_owner.user)
        get_resp_succ = self.api_client.get(f"/{self.project}/api/v1/{model_pk}/edit/")
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
        get_resp_pend = self.api_client.get(f"/{self.project}/api/v1/{model_pk}/")
        assert_status(202, get_resp_pend, "poll_simulation")

    def check_simulation_finished(self, model_pk: int):
        self.sim = Simulation.objects.get(project=self.project, model_pk=model_pk)

        # Test permissions on /outputs/api/ endpoint.
        self.api_client.logout()
        not_authed = self.api_client.put(
            "/outputs/api/",
            data=dict(
                json.loads(self.mockcompute.outputs), **{"task_id": self.sim.job_id}
            ),
            format="json",
        )
        assert_status(401, not_authed, "put_outputs_not_authed")

        self.api_client.force_login(self.sim.project.owner.user)
        no_perms = self.api_client.put(
            "/outputs/api/",
            data=dict(
                json.loads(self.mockcompute.outputs), **{"task_id": self.sim.job_id}
            ),
            format="json",
        )
        assert_status(401, not_authed, "put_outputs_no_perms")
        self.api_client.logout()

        resp = self.api_client.put(
            "/outputs/api/",
            data=dict(
                json.loads(self.mockcompute.outputs), **{"task_id": self.sim.job_id}
            ),
            format="json",
            **self.project.cluster.headers(),
        )
        if resp.status_code != 200:
            raise Exception(
                f"Status code: {resp.status_code}\n {json.dumps(resp.data, indent=4)}"
            )
        self.client.force_login(self.sim_owner.user)
        self.api_client.force_login(self.sim_owner.user)

        get_resp_succ = self.api_client.get(f"/{self.project}/api/v1/{model_pk}/")
        assert_status(200, get_resp_succ, "check_simulation_finished")
        model_pk = get_resp_succ.data["model_pk"]
        self.sim.refresh_from_db()
        assert self.sim.status == "SUCCESS"
        assert self.sim.outputs
        assert self.sim.traceback is None

    def view_inputs_from_model_pk(self, model_pk: int):
        get_resp_inputs = self.api_client.get(
            f"/{self.project}/api/v1/{model_pk}/edit/"
        )
        assert_status(200, get_resp_inputs, "view_inputs_from_model_pk")
        data = get_resp_inputs.data
        assert "adjustment" in data
        assert data["sim"]["model_pk"] == model_pk

        edit_page = self.client.get(f"/{self.project}/{model_pk}/edit/")
        assert_status(200, edit_page, "view_inputs_from_model_pk")

    def set_sim_description(self, model_pk: int):
        sim = Simulation.objects.get(
            project__owner__user__username__iexact=self.owner,
            project__title__iexact=self.title,
            model_pk=model_pk,
        )
        self.api_client.force_login(sim.owner.user)
        get_sim_resp = self.api_client.get(f"/{self.project}/api/v1/{model_pk}/remote/")
        assert_status(200, get_sim_resp, "set_sim_description")
        data = get_sim_resp.data

        assert data["title"] == sim.title == f"{sim.project} #{sim.model_pk}"
        assert data["owner"] == str(sim.owner)
        assert sim.parent_sim == None

        put_desc_resp = self.api_client.put(
            f"/{self.project}/api/v1/{model_pk}/", data={"title": "My sim"}
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
            output_id = self.sim.outputs["outputs"]["renderable"]["outputs"][0]["id"]
            api_paths = [
                f"/{self.project}/api/v1/{model_pk}/remote/",
                f"/{self.project}/api/v1/{model_pk}/",
                f"/{self.project}/api/v1/{model_pk}/edit/",
            ]
            paths = [
                f"/{self.project}/{model_pk}/",
                f"/{self.project}/{model_pk}/edit/",
                f"/storage/screenshots/{output_id}.png",
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
        self.api_client.force_login(self.sim_owner.user)
        self.client.force_login(self.sim_owner.user)
        fetch_sims(200)

        self.api_client.logout()
        self.client.logout()
        if self.project.is_public:
            fetch_sims(200)
        else:
            fetch_sims([404, 403])

        # test with private sim
        self.sim.is_public = False
        self.sim.save()
        self.api_client.force_login(self.sim.owner.user)
        self.client.force_login(self.sim_owner.user)

        fetch_sims(200)

        self.api_client.logout()
        self.client.logout()
        fetch_sims([403, 404])


@pytest.fixture(params=[True, False])
def sponsored_matchups(request, db, pro_profile):
    sponsor = Profile.objects.get(user__username="sponsor")
    matchups = Project.objects.get(title="Matchups", owner__user__username="hdoupe")
    matchups.is_public = request.param
    if not matchups.is_public:
        replace_owner(matchups, pro_profile)
    matchups.sponsor = sponsor
    matchups.save()
    return matchups


@pytest.fixture
def paid_matchups(db):
    from webapp.apps.billing.models import Plan

    matchups = Project.objects.get(title="Matchups", owner__user__username="hdoupe")
    matchups.sponsor = None
    matchups.owner.user.customer.update_plan(
        Plan.objects.get(nickname=f"Monthly Pro Plan")
    )
    matchups.refresh_from_db()
    matchups.save()
    return matchups


@pytest.mark.requires_stripe
@pytest.mark.usefixtures("paid_matchups")
@pytest.mark.django_db
class TestPaidModel(CoreTestMixin):
    class MatchupsMockCompute(MockCompute):
        outputs = read_outputs("Matchups_v1")

    owner = "hdoupe"
    title = "Matchups"
    mockcompute = MatchupsMockCompute

    def test_runmodel_no_existing_subs(
        self, monkeypatch, client, api_client, comp_api_user,
    ):
        """
        Test lifetime of submitting a model.
        """
        profile = gen_blank_customer(
            username="new-cust", email="tester@email.com", password="heyhey2222"
        )

        set_auth_token(api_client, profile.user)

        rmm = RunMockModel(
            owner=self.owner,
            title=self.title,
            defaults=self.defaults(),
            inputs=self.inputs_ok(),
            errors_warnings=self.errors_warnings(),
            client=client,
            api_client=api_client,
            comp_api_user=comp_api_user,
            monkeypatch=monkeypatch,
            mockcompute=self.mockcompute,
            test_lower=False,
        )
        rmm.run()

    def test_runmodel_existing_subs(
        self, monkeypatch, client, api_client, profile, comp_api_user,
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
            comp_api_user=comp_api_user,
            monkeypatch=monkeypatch,
            mockcompute=self.mockcompute,
            test_lower=False,
        )
        rmm.run()


@pytest.mark.usefixtures("sponsored_matchups")
@pytest.mark.usefixtures("customer_pro_by_default")
@pytest.mark.django_db
class TestAsyncAPI(CoreTestMixin):
    class MatchupsMockCompute(MockCompute):
        outputs = read_outputs("Matchups_v1")

    title = "Matchups"
    mockcompute = MatchupsMockCompute

    def errors_warnings(self):
        return {"matchup": {"errors": {}, "warnings": {}}}

    def test_get_inputs(self, api_client):
        defaults = self.defaults()
        resp_data = {"status": "SUCCESS", **defaults}
        with requests_mock.Mocker() as mock:
            mock.register_uri(
                "POST",
                f"{self.project.cluster.url}/{self.project}/",
                text=json.dumps(resp_data),
            )
            resp = api_client.get(f"/{self.project}/api/v1/inputs/")
            if self.project.is_public:
                assert resp.status_code == 200
            else:
                assert resp.status_code == 404
                return
            ioutils = get_ioutils(self.project)
            exp = ioutils.model_parameters.defaults()
            assert exp == resp.data

    @pytest.mark.parametrize("use_api", [True, False])
    def test_new_sim(self, use_api, client, api_client, profile):
        self.project.assign_role("read", profile.user)
        resp = client.get(f"/{self.project}/")
        assert_status(200 if self.project.is_public else 404, resp, "test_new_sim")

        new_resp = client.get(f"/{self.project}/new/")
        assert_status(200 if self.project.is_public else 404, new_resp, "test_new_sim")

        api_client.force_login(profile.user)
        client.force_login(profile.user)
        if use_api:
            auth_resp = api_client.post(f"/{self.project}/api/v1/new/")
            assert_status(201, auth_resp, "test_new_sim_api")
            sim_url = auth_resp.data["sim"]["gui_url"]
        else:
            auth_resp = client.get(f"/{self.project}/new/")
            assert_status(302, auth_resp, "test_new_sim_gui")
            sim_url = auth_resp.url

        sim_resp = client.get(sim_url)
        assert_status(200, sim_resp, sim_url)

        model_pk = int(sim_url.split("/")[3])

        sim = Simulation.objects.get(project=self.project, model_pk=model_pk,)

        assert sim.status == "STARTED"
        assert sim.inputs.status == "STARTED"

        api_client.logout()
        exp_unauthed_status = 403 if self.project.is_public else 404
        anon_resp = api_client.post(
            sim.get_absolute_api_url(),
            data={"adjustment": {}, "meta_parameters": {}},
            format="json",
        )
        assert_status(exp_unauthed_status, anon_resp, "test_new_sim_anon")

        u = sim.project.owner.user
        set_auth_token(api_client, u)
        anon_resp = api_client.post(
            sim.get_absolute_api_url(),
            data={"adjustment": {}, "meta_parameters": {}},
            format="json",
        )
        assert_status(exp_unauthed_status, anon_resp, "test_new_sim_oth_user")

        defaults = self.defaults()
        inputs_resp_data = {"status": "SUCCESS", **defaults}
        adj_resp_data = {"task_id": str(uuid.uuid4())}
        with requests_mock.Mocker() as mock:
            mock.register_uri(
                "POST",
                f"{self.project.cluster.url}/{self.project}/",
                json=lambda request, context: {
                    "defaults": inputs_resp_data,
                    "parse": adj_resp_data,
                }[request.json()["task_name"]],
            )
            api_client.force_login(sim.owner.user)
            resp = api_client.get(sim.inputs.get_absolute_api_url())
            assert_status(200, resp, "test_new_sim_inputs")
            resp = api_client.get(sim.get_absolute_api_url())
            assert_status(200, resp, "test_new_sim_outputs")

            api_client.force_login(profile.user)
            if not self.project.is_public:
                self.project.assign_role(None, profile.user)
                anon_resp = api_client.post(
                    sim.get_absolute_api_url(),
                    data={"adjustment": {}, "meta_parameters": {}},
                    format="json",
                )
                assert_status(404, anon_resp, "test_new_sim_owner-private")
                self.project.assign_role("read", profile.user)

            anon_resp = api_client.post(
                sim.get_absolute_api_url(),
                data={"adjustment": {}, "meta_parameters": {}},
                format="json",
            )
            assert_status(201, anon_resp, "test_new_sim_owner")

    def test_post_inputs(self, api_client, profile):
        defaults = self.defaults()
        resp_data = {"status": "SUCCESS", **defaults}
        meta_params = {"meta_parameters": self.inputs_ok()["meta_parameters"]}
        with requests_mock.Mocker() as mock:
            print(
                "mocking", f"{self.project.cluster.url}/{self.project}/inputs",
            )
            mock.register_uri(
                "POST",
                f"{self.project.cluster.url}/{self.project}/",
                json=lambda request, context: {
                    "defaults": resp_data,
                    "version": {"status": "SUCCESS", "version": "1.0.0"},
                }[request.json()["task_name"]],
            )
            if not self.project.is_public:
                no_access = api_client.post(
                    f"/{self.project}/api/v1/inputs/", data=meta_params, format="json",
                )
                assert no_access.status_code == 404
                api_client.force_login(profile.user)
                self.project.assign_role("read", profile.user)

            resp = api_client.post(
                f"/{self.project}/api/v1/inputs/", data=meta_params, format="json",
            )
            assert resp.status_code == 200

            ioutils = get_ioutils(self.project)
            exp = ioutils.model_parameters.defaults(meta_params["meta_parameters"])
            assert exp == resp.data

    @pytest.mark.parametrize("test_lower", [False, True])
    def test_runmodel(
        self, monkeypatch, client, api_client, profile, comp_api_user, test_lower,
    ):
        """
        Test lifetime of submitting a model.
        """
        set_auth_token(api_client, profile.user)
        api_client.force_login(profile.user)
        self.project.assign_role("read", profile.user)
        rmm = RunMockModel(
            owner=self.owner,
            title=self.title,
            defaults=self.defaults(),
            inputs=self.inputs_ok(),
            errors_warnings=self.errors_warnings(),
            client=client,
            api_client=api_client,
            comp_api_user=comp_api_user,
            monkeypatch=monkeypatch,
            mockcompute=self.mockcompute,
            test_lower=test_lower,
        )
        rmm.run()

    def test_perms(
        self, monkeypatch, client, api_client, comp_api_user,
    ):
        """
        Test unable to post anon params.
        """
        (collab,) = gen_collabs(1, plan="pro")
        kwargs = dict(
            owner=self.owner,
            title=self.title,
            defaults=self.defaults(),
            inputs=self.inputs_ok(),
            errors_warnings=self.errors_warnings(),
            client=client,
            api_client=api_client,
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
        if self.project.is_public:
            assert excinfo.value.act_status == 403
        else:
            assert excinfo.value.act_status == 404

        proj = self.project
        proj.sponsor = None
        proj.save()

        api_client.force_login(collab.user)
        if not self.project.is_public:
            self.project.assign_role("read", collab.user)

        rmm = RunMockModel(**kwargs)
        rmm.run()

        collab.user.customer.delete()
        collab.save()

        api_client.force_login(collab.user)

        rmm = RunMockModel(**kwargs)
        with pytest.raises(ResponseStatusException) as excinfo:
            rmm.run()
        assert excinfo.value.stage == "post_adjustment", excinfo.value.act_status
        assert excinfo.value.exp_status == 201
        assert excinfo.value.act_status == 403

    @pytest.mark.parametrize("test_lower", [False, True])
    def test_fork(
        self, monkeypatch, client, api_client, comp_api_user, test_lower,
    ):
        """
        Test creating and forking a sim.
        """
        (sim_owner, pro_sim_collab) = gen_collabs(2, plan="pro")
        (free_sim_collab,) = gen_collabs(1)
        api_client.force_login(sim_owner.user)
        if not self.project.is_public:
            self.project.assign_role("read", sim_owner.user)
        rmm = RunMockModel(
            owner=self.owner,
            title=self.title,
            defaults=self.defaults(),
            inputs=self.inputs_ok(),
            errors_warnings=self.errors_warnings(),
            client=client,
            api_client=api_client,
            comp_api_user=comp_api_user,
            monkeypatch=monkeypatch,
            mockcompute=self.mockcompute,
            test_lower=test_lower,
        )
        rmm.run()
        assert rmm.sim.is_public is False
        rmm.sim.owner = sim_owner

        # Test free plan user cannot fork private simulation even if they
        # have read access.
        self.project.assign_role("read", free_sim_collab.user)
        rmm.sim.assign_role("read", free_sim_collab.user)

        # Temporarily remove perms to test fork endpoint.
        if not self.project.is_public:
            self.project.assign_role(None, free_sim_collab.user)

        api_client.force_login(free_sim_collab.user)
        resp = api_client.post(f"/{self.project}/api/v1/{rmm.sim.model_pk}/fork/")
        if not self.project.is_public:
            assert resp.status_code == 404
            self.project.assign_role("read", free_sim_collab.user)
            resp = api_client.post(f"/{self.project}/api/v1/{rmm.sim.model_pk}/fork/")

        assert resp.status_code == 201, f"Got {resp.status_code}"

        # This created a forked sim.
        assert free_sim_collab.sims.count() == 1
        sim: Simulation = free_sim_collab.sims.first()
        assert sim.parent_sim == rmm.sim

        # Create two more private sims (subtract initial private sim and the one that will cause 400)
        for _ in range(FREE_PRIVATE_SIMS - 2):
            resp = api_client.post(f"/{self.project}/api/v1/{rmm.sim.model_pk}/fork/")
            assert resp.status_code == 201, f"Got code: {resp.status_code}"
        # Pushes user over free tier limit.
        resp = api_client.post(f"/{self.project}/api/v1/{rmm.sim.model_pk}/fork/")
        assert resp.status_code == 400, f"Got code: {resp.status_code}"

        # Test free plan user can fork public sims.
        rmm.sim.is_public = True
        rmm.sim.save()
        resp = api_client.post(f"/{self.project}/api/v1/{rmm.sim.model_pk}/fork/")
        assert resp.status_code == 201

        # Test pro plan user can fork private simulation.
        self.project.assign_role("read", pro_sim_collab.user)
        rmm.sim.assign_role("read", pro_sim_collab.user)
        rmm.sim.is_public = False
        rmm.sim.save()
        api_client.force_login(pro_sim_collab.user)
        resp = api_client.post(f"/{self.project}/api/v1/{rmm.sim.model_pk}/fork/")
        assert resp.status_code == 201

        # Test anon user cannot view private forked sim.
        api_client.logout()
        private_sim = pro_sim_collab.sims.first()
        resp = api_client.get(f"/{self.project}/api/v1/{private_sim.model_pk}/")
        exp_unauthed_code = 403 if self.project.is_public else 404
        assert resp.status_code == exp_unauthed_code

        # Test anon user can view forked sim only applicable if project is public.
        if self.project.is_public:
            public_sim = free_sim_collab.sims.first()
            public_sim.is_public = True
            public_sim.save()
            resp = api_client.get(f"/{self.project}/api/v1/{public_sim.model_pk}/")
            assert resp.status_code == 200

        # Test unable to fork sim while pending.
        api_client.force_login(pro_sim_collab.user)
        rmm.sim.status = "PENDING"
        rmm.sim.save()
        resp = api_client.post(f"/{self.project}/api/v1/{rmm.sim.model_pk}/fork/")
        assert resp.status_code == 400
        assert resp.data["fork"]


def test_placeholder_page(db, client):
    title = "Matchups"
    owner = "hdoupe"
    project = Project.objects.get(
        title__iexact=title, owner__user__username__iexact=owner
    )
    project.latest_tag = None
    project.save()
    resp = client.get(f"/{owner}/{title}/")
    assert resp.status_code == 200
    project.latest_tag = Tag.objects.create(
        project=project, image_tag="v1", cpu=project.cpu, memory=project.memory,
    )
    project.save()
    resp = client.get(f"/{owner}/{title}/")
    assert resp.status_code == 200


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
    db,
    sponsored_matchups,
    client,
    api_client,
    get_inputs,
    meta_param_dict,
    customer_pro_by_default,
):
    """
    Test responses on v0 outputs.
    - public
    - private
    - title update
    """
    (user,) = gen_collabs(1, plan="pro")
    if not sponsored_matchups.is_public:
        sponsored_matchups.assign_role("read", user.user)
    inputs = _submit_inputs("Matchups", get_inputs, meta_param_dict, user)

    _, submit_sim = _submit_sim(inputs)
    sim = submit_sim.submit()
    sim.status = "SUCCESS"
    sim.is_public = True
    v0_outputs = json.loads(read_outputs("Matchups_v0"))
    sim.outputs = v0_outputs
    sim.save()

    assert sim.outputs_version() == "v0"

    # Test public responses.
    if sponsored_matchups.is_public:
        exp_unauthed_redirect_status = 302
        exp_unauthed_status = 200
    else:
        exp_unauthed_status = exp_unauthed_redirect_status = 404
    resp = client.get(f"/{sim.project.owner}/{sim.project.title}/{sim.model_pk}/")
    assert_status(exp_unauthed_redirect_status, resp, "v0-redirect")
    resp = client.get(f"/{sim.project.owner}/{sim.project.title}/{sim.model_pk}/v0/")
    assert_status(exp_unauthed_status, resp, "v0")
    resp = client.get(f"/{sim.project.owner}/{sim.project.title}/{sim.model_pk}/edit/")
    assert_status(exp_unauthed_status, resp, "v0-edit")
    resp = api_client.get(
        f"/{sim.project.owner}/{sim.project.title}/api/v1/{sim.model_pk}/"
    )
    assert_status(exp_unauthed_status, resp, "v0-api-get")
    resp = api_client.get(
        f"/{sim.project.owner}/{sim.project.title}/api/v1/{sim.model_pk}/edit/"
    )
    assert_status(exp_unauthed_status, resp, "v0-edit-api-get")

    # Test private responses.
    s = Simulation.objects.get(pk=sim.pk)
    s.is_public = False
    s.save()

    if sponsored_matchups.is_public:
        forbidden_status = 403
    else:
        forbidden_status = 404
    resp = client.get(f"/{sim.project.owner}/{sim.project.title}/{sim.model_pk}/")
    assert_status(forbidden_status, resp, "v0-redirect")
    resp = client.get(f"/{sim.project.owner}/{sim.project.title}/{sim.model_pk}/v0/")
    assert_status(forbidden_status, resp, "v0")
    resp = client.get(f"/{sim.project.owner}/{sim.project.title}/{sim.model_pk}/edit/")
    assert_status(forbidden_status, resp, "v0-edit")
    resp = api_client.get(
        f"/{sim.project.owner}/{sim.project.title}/api/v1/{sim.model_pk}/"
    )
    assert_status(forbidden_status, resp, "v0-api-get")

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


class TestCollaboration:
    def test_add_author_flow(
        self,
        db,
        sponsored_matchups,
        client,
        api_client,
        get_inputs,
        meta_param_dict,
        pro_profile,
        customer_pro_by_default,
    ):
        """
        Test full add new author flow.
        """
        sponsored_matchups.assign_role("read", pro_profile.user)
        inputs = _submit_inputs("Matchups", get_inputs, meta_param_dict, pro_profile)

        _, submit_sim = _submit_sim(inputs)
        sim = submit_sim.submit()
        sim.status = "SUCCESS"
        sim.is_public = False
        sim.save()

        assert sim.authors.all().count() == 1 and sim.authors.get(pk=sim.owner.pk)

        collab = next(gen_collabs(1))

        # Permission denied on unauthed user
        resp = api_client.put(
            f"{sim.get_absolute_api_url()}authors/",
            data={"authors": [{"username": collab.user.username}]},
            format="json",
        )
        assert_status(403, resp, "denied_authors")

        # Permission denied if user is not owner of sim.
        api_client.force_login(collab.user)
        resp = api_client.put(
            f"{sim.get_absolute_api_url()}authors/",
            data={"authors": [{"username": collab.user.username}]},
            format="json",
        )
        if sponsored_matchups.is_public:
            not_authed_code = 403
        else:
            not_authed_code = 404
        assert_status(not_authed_code, resp, "denied_authors")

        # Successful update
        api_client.force_login(pro_profile.user)
        resp = api_client.put(
            f"{sim.get_absolute_api_url()}authors/",
            data={"authors": [{"username": collab.user.username}]},
            format="json",
        )

        if not sponsored_matchups.is_public:
            assert_status(400, resp, "collab doesn't have access to app")
            sponsored_matchups.assign_role("read", collab.user)
            resp = api_client.put(
                f"{sim.get_absolute_api_url()}authors/",
                data={"authors": [{"username": collab.user.username}]},
                format="json",
            )

        assert_status(200, resp, "success_authors")

        sim = Simulation.objects.get(pk=sim.pk)
        assert sim.authors.all().count() == 1 and sim.authors.get(pk=sim.owner.pk)
        assert sim.pending_permissions.all().count() == 1 and sim.pending_permissions.all().get(
            profile=collab
        )
        pp = sim.pending_permissions.first()

        # Test user redirected to login if not authed.
        resp = client.get(pp.get_absolute_url())
        assert_status(302, resp, "pending_redirect_to_login")
        assert resp.url == f"/users/login/?next={pp.get_absolute_url()}"

        # Login profile, go to permission confirmation page.
        client.force_login(user=collab.user)
        resp = client.get(pp.get_absolute_url())
        assert_status(200, resp, "get_permissions_pending")
        assert "comp/permissions/confirm.html" in [t.name for t in resp.templates]
        # Test user granted access to private simulation
        resp = client.get(pp.sim.get_absolute_url())
        assert_status(200, resp, "potential_sim_author_has_read_access")
        # GET link for granting permission.
        resp = client.get(pp.get_absolute_grant_url())
        assert_status(302, resp, "grant_permissions")
        assert resp.url == sim.get_absolute_url()

        sim = Simulation.objects.get(pk=sim.pk)
        assert sim.authors.all().count() == 2
        assert sim.authors.filter(pk__in=[pro_profile.pk, collab.pk]).count() == 2
        assert sim.pending_permissions.count() == 0

    def test_add_authors_api(
        self,
        db,
        sponsored_matchups,
        client,
        api_client,
        get_inputs,
        meta_param_dict,
        customer_pro_by_default,
    ):
        """
        Test add authors api endpoints.
        """
        (collab1, collab2,) = gen_collabs(2, plan="pro")
        sponsored_matchups.assign_role("read", collab1.user)
        inputs = _submit_inputs("Matchups", get_inputs, meta_param_dict, collab1)

        _, submit_sim = _submit_sim(inputs)
        sim = submit_sim.submit()
        sim.status = "SUCCESS"
        sim.is_public = True
        sim.save()

        assert sim.authors.all().count() == 1 and sim.authors.get(pk=sim.owner.pk)

        # first create a pending permission through the api
        api_client.force_login(collab1.user)
        resp = api_client.put(
            f"{sim.get_absolute_api_url()}authors/",
            data={"authors": [{"username": collab2.user.username}]},
            format="json",
        )
        if not sponsored_matchups.is_public:
            assert_status(400, resp, "user doesn't have access to app")
            sponsored_matchups.assign_role("read", collab2.user)
            resp = api_client.put(
                f"{sim.get_absolute_api_url()}authors/",
                data={"authors": [{"username": collab2.user.username}]},
                format="json",
            )

        assert_status(200, resp, "success_authors")

        # check that resubmit has no effect on non-expired permissions.
        init_pp = sim.pending_permissions.get(profile__pk=collab2.pk)
        assert PendingPermission.objects.count() == 1

        resp = api_client.put(
            f"{sim.get_absolute_api_url()}authors/",
            data={"authors": [{"username": collab2.user.username}]},
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
            data={"authors": [{"username": collab2.user.username}]},
            format="json",
        )
        assert_status(200, resp, "success_authors")

        # Check that stale permission is removed and a new one is added.
        assert PendingPermission.objects.count() == 1
        assert PendingPermission.objects.filter(pk=init_pp.pk).count() == 0
        new_pp = sim.pending_permissions.get(profile__pk=collab2.pk)
        assert new_pp.sim == sim

    def test_delete_author(
        self,
        db,
        sponsored_matchups,
        client,
        api_client,
        get_inputs,
        meta_param_dict,
        customer_pro_by_default,
    ):
        """
        Test delete author from simulation.
        - owner cannot be deleted from author list.
        - check delete before permission approval.
        - check delete of existing author.
        - 404 on dne or unassociated author.
        - author can remove themselves as author.
        """
        (collab1, collab2,) = gen_collabs(2, plan="pro")
        sponsored_matchups.assign_role("read", collab1.user)
        inputs = _submit_inputs("Matchups", get_inputs, meta_param_dict, collab1)

        _, submit_sim = _submit_sim(inputs)
        sim = submit_sim.submit()
        sim.status = "SUCCESS"
        sim.is_public = True
        sim.save()

        assert sim.authors.all().count() == 1 and sim.authors.get(pk=sim.owner.pk)

        # test not allowed to delete owner of simulation from authors.
        api_client.force_login(collab1.user)
        resp = api_client.delete(f"{sim.get_absolute_api_url()}authors/{sim.owner}/")
        assert_status(400, resp, "cannot_delete_sim_owner")
        sim = Simulation.objects.get(pk=sim.pk)
        assert sim.authors.all().count() == 1 and sim.authors.get(pk=sim.owner.pk)

        # first create a pending permission through the api.
        resp = api_client.put(
            f"{sim.get_absolute_api_url()}authors/",
            data={"authors": [{"username": collab2.user.username}]},
            format="json",
        )
        if not sponsored_matchups.is_public:
            assert_status(400, resp, "user doesn't have access to app")
            sponsored_matchups.assign_role("read", collab2.user)
            resp = api_client.put(
                f"{sim.get_absolute_api_url()}authors/",
                data={"authors": [{"username": collab2.user.username}]},
                format="json",
            )

        assert_status(200, resp, "success_authors")

        init_pp = sim.pending_permissions.get(profile__pk=collab2.pk)

        # test delete author before they approve request.
        resp = api_client.delete(f"{sim.get_absolute_api_url()}authors/{collab2}/")
        assert_status(204, resp, "delete_pending_author")
        assert PendingPermission.objects.filter(id=init_pp.id).count() == 0
        sim = Simulation.objects.get(pk=sim.pk)
        assert sim.authors.all().count() == 1 and sim.authors.get(pk=sim.owner.pk)

        # test delete author.
        api_client.force_login(collab1.user)
        resp = api_client.put(
            f"{sim.get_absolute_api_url()}authors/",
            data={"authors": [{"username": collab2.user.username}]},
            format="json",
        )
        assert_status(200, resp, "success_authors")

        new_pp = sim.pending_permissions.get(profile__pk=collab2.pk)
        new_pp.add_author()
        assert sim.authors.all().count() == 2 and sim.authors.get(pk=collab2.pk)

        resp = api_client.delete(f"{sim.get_absolute_api_url()}authors/{collab2}/")
        assert_status(204, resp, "delete_pending_author")
        assert PendingPermission.objects.filter(id=init_pp.id).count() == 0
        sim = Simulation.objects.get(pk=sim.pk)
        assert sim.authors.all().count() == 1 and sim.authors.get(pk=sim.owner.pk)

        # test not found
        resp = api_client.delete(f"{sim.get_absolute_api_url()}authors/{collab2}/")
        assert_status(404, resp, "delete_author_already_deleted")
        resp = api_client.delete(f"{sim.get_absolute_api_url()}authors/abcd/")
        assert_status(404, resp, "delete_author_profile_dne")

        # test unauth'ed user does not have access.
        api_client.logout()
        resp = api_client.delete(f"{sim.get_absolute_api_url()}authors/{collab2}/")
        assert_status(403, resp, "delete_author_must_be_auth'ed")

        # test profile can remove themselves.
        api_client.force_login(collab1.user)
        resp = api_client.put(
            f"{sim.get_absolute_api_url()}authors/",
            data={"authors": [{"username": collab2.user.username}]},
            format="json",
        )
        assert_status(200, resp, "success_authors")

        api_client.force_login(collab2.user)
        resp = api_client.delete(f"{sim.get_absolute_api_url()}authors/{collab2}/")
        assert_status(204, resp, "author_can_delete_themselves")

        # test must have write access or be removing oneself
        u = User.objects.create_user("danger", "danger@example.com", "heyhey2222")
        create_profile_from_user(u)
        danger = Profile.objects.get(user__username="danger")
        api_client.force_login(danger.user)
        resp = api_client.delete(f"{sim.get_absolute_api_url()}authors/{collab2}/")
        if not sponsored_matchups.is_public:
            assert_status(404, resp, "user needs access access to app")
            sponsored_matchups.assign_role("read", danger.user)
            resp = api_client.delete(f"{sim.get_absolute_api_url()}authors/{collab2}/")

        assert_status(403, resp, "auth'ed user cannot delete authors")

    def test_sim_read_access_management(
        self,
        db,
        sponsored_matchups,
        client,
        api_client,
        get_inputs,
        meta_param_dict,
        pro_profile,
        customer_pro_by_default,
    ):
        """
        Test grant/remove read access to private simulation.
        - Assert user does not have read access
        - Check user without read access cannot add themselves
        - Grant read access to user successfully
        - Make sure user with read access cannot add others to list
        - Remove read access from user successfully.
        """
        sponsored_matchups.assign_role("read", pro_profile.user)
        inputs = _submit_inputs("Matchups", get_inputs, meta_param_dict, pro_profile)

        _, submit_sim = _submit_sim(inputs)
        sim = submit_sim.submit()
        sim.status = "SUCCESS"
        sim.outputs = json.loads(read_outputs("Matchups_v1"))
        sim.is_public = False
        sim.save()

        collabs = list(gen_collabs(2))

        # Check user does not have access to sim
        api_client.force_login(collabs[0].user)
        resp = api_client.get(sim.get_absolute_api_url())
        if not sponsored_matchups.is_public:
            assert_status(404, resp, "user does not have read access to app")
            sponsored_matchups.assign_role("read", collabs[0].user)
            resp = api_client.get(sim.get_absolute_api_url())

        assert_status(403, resp, "user does not have read access to sim yet")

        # Check user cannot update read access list
        resp = api_client.put(
            f"{sim.get_absolute_api_url()}access/",
            data=[{"username": str(collabs[0]), "role": "read"}],
            format="json",
        )
        assert_status(403, resp, "user cannot update read access")

        # Grant read access to user
        api_client.force_login(sim.owner.user)
        resp = api_client.put(
            f"{sim.get_absolute_api_url()}access/",
            data=[{"username": str(collabs[0]), "role": "read"}],
            format="json",
        )
        assert_status(204, resp, "user granted read access")

        api_client.force_login(collabs[0].user)
        resp = api_client.get(sim.get_absolute_api_url())
        assert_status(200, resp, "user has read access to sim")

        # Check user with read access cannot grant others read access
        if not sponsored_matchups.is_public:
            sponsored_matchups.assign_role("read", collabs[1].user)
        resp = api_client.put(
            f"{sim.get_absolute_api_url()}access/",
            data=[{"username": str(collabs[1]), "role": "read"}],
            format="json",
        )
        assert_status(403, resp, "user granted read access")

        # Remove read access from user
        api_client.force_login(sim.owner.user)
        resp = api_client.put(
            f"{sim.get_absolute_api_url()}access/",
            data=[{"username": str(collabs[0]), "role": None}],
            format="json",
        )
        assert_status(204, resp, "user no longer has read access")

        api_client.force_login(collabs[0].user)
        resp = api_client.get(sim.get_absolute_api_url())
        assert_status(403, resp, "user no longer has read access to sim")

    def test_collaboration(
        self,
        db,
        monkeypatch,
        sponsored_matchups,
        client,
        api_client,
        get_inputs,
        meta_param_dict,
        pro_profile,
        customer_pro_by_default,
    ):
        sponsored_matchups.assign_role("read", pro_profile.user)
        inputs = _submit_inputs("Matchups", get_inputs, meta_param_dict, pro_profile)

        _, submit_sim = _submit_sim(inputs)
        sim = submit_sim.submit()
        sim.status = "SUCCESS"
        sim.outputs = json.loads(read_outputs("Matchups_v1"))
        sim.is_public = False
        sim.save()

        collabs = list(gen_collabs(2))
        for collab in collabs:
            sponsored_matchups.assign_role("read", collab.user)

        # Grant read access to user
        api_client.force_login(sim.owner.user)
        for collab in collabs:
            resp = api_client.put(
                f"{sim.get_absolute_api_url()}access/",
                data=[{"username": str(collab), "role": "read"}],
                format="json",
            )
            assert_status(204, resp, f"{str(collab)} granted read access")

        # remove read acccess from 2 users
        for collab in collabs[:2]:
            resp = api_client.put(
                f"{sim.get_absolute_api_url()}access/",
                data=[{"username": str(collab), "role": None}],
                format="json",
            )
            assert_status(204, resp, f"{str(collab)} revoked read access")

        # add as authors
        for collab in collabs:
            resp = api_client.put(
                f"{sim.get_absolute_api_url()}authors/",
                data={"authors": [{"username": str(collab)}]},
                format="json",
            )
            assert_status(200, resp, f"add author {str(collab)}")

    def test_make_sim_private_with_collabs(
        self, db, client, api_client, get_inputs, meta_param_dict,
    ):
        """
        Test collaborator resource usage limits.
        - Test add 3 collaborators to public sim is OK.
        - Test user can not make sim private afterwards.
        """
        sponsored_matchups = Project.objects.get(
            title="Matchups", owner__user__username="hdoupe"
        )
        sponsored_matchups.sponsor = sponsored_matchups.owner
        sponsored_matchups.save()

        (sim_owner, collab1, collab2, collab3) = gen_collabs(4)
        collabs = (collab1, collab2, collab3)
        for collab in (sim_owner, collab1, collab2, collab3):
            sponsored_matchups.assign_role("read", collab.user)

        inputs = _submit_inputs("Matchups", get_inputs, meta_param_dict, sim_owner)

        _, submit_sim = _submit_sim(inputs)
        sim = submit_sim.submit()
        sim.status = "SUCCESS"
        sim.outputs = json.loads(read_outputs("Matchups_v1"))
        sim.is_public = True
        sim.save()

        # Grant read access to users
        api_client.force_login(sim.owner.user)
        for collab in collabs:
            resp = api_client.put(
                f"{sim.get_absolute_api_url()}access/",
                data=[{"username": str(collab), "role": "read"}],
                format="json",
            )
            assert_status(204, resp, f"{str(collab)} granted read access")

        resp = api_client.put(sim.get_absolute_api_url(), data={"is_public": False})
        sim.refresh_from_db()
        assert_status(200, resp, "make private with collabs")

    def test_private_simulation_limit(
        self, db, client, api_client, get_inputs, meta_param_dict,
    ):
        """
        Test collaborator resource usage limits.
        - Test creating FREE_PRIVATE_SIMS - 1 is ok
        - Test making the FREE_PRIVATE_SIMS'th one causes an error.
        """
        sponsored_matchups = Project.objects.get(
            title="Matchups", owner__user__username="hdoupe"
        )
        sponsored_matchups.sponsor = sponsored_matchups.owner
        sponsored_matchups.save()

        (sim_owner,) = gen_collabs(1)
        sponsored_matchups.assign_role("read", sim_owner.user)

        sims = []
        for _ in range(FREE_PRIVATE_SIMS + 1):
            inputs = _submit_inputs("Matchups", get_inputs, meta_param_dict, sim_owner)

            _, submit_sim = _submit_sim(inputs)
            sim = submit_sim.submit()
            sim.status = "SUCCESS"
            sim.outputs = json.loads(read_outputs("Matchups_v1"))
            sim.is_public = True
            sim.save()
            sims.append(sim)

        for sim in sims[:-1]:
            api_client.force_login(sim.owner.user)
            resp = api_client.put(sim.get_absolute_api_url(), data={"is_public": False})
            assert_status(200, resp, "ok to make sims private")
            sim.refresh_from_db()
            assert not sim.is_public

        api_client.force_login(sims[-1].owner.user)
        resp = api_client.put(
            sims[-1].get_absolute_api_url(), data={"is_public": False}
        )
        assert_status(400, resp, "can't make FREE_PRIVATE_SIMS'th private")
        assert resp.data == {
            "simulation": {
                "msg": PrivateSimException.msg,
                "upgrade_to": "pro",
                "resource": PrivateSimException.resource,
                "test_name": "make_simulation_private",
            }
        }
        sims[-1].refresh_from_db()
        assert sims[-1].is_public


def test_list_sim_api(db, api_client, get_inputs, meta_param_dict):
    (user,) = gen_collabs(1, plan="pro")
    sims, modeler_sims, tester_sims = _shuffled_sims(user, get_inputs, meta_param_dict)
    # test can't access api/v1/sims if not authenticated.
    resp = api_client.get("/api/v1/sims")
    assert_status(403, resp, "unauthed_list_sims")
    resp = api_client.get("/api/v1/sims?ordering=project__title")
    assert_status(403, resp, "unauthed_list_sims")

    # test sims are public and view-able by default.
    resp = api_client.get(f"/api/v1/sims/{user}")
    assert_status(200, resp, "unauthed_list_profile_sims")
    assert len(resp.data["results"]) == 6

    # Make sims private now.
    for sim in sims:
        sim.is_public = False
        sim.save()

    # test only public sims are shown on profile page.
    tester_sims[1].is_public = True
    tester_sims[1].save()
    resp = api_client.get(f"/api/v1/sims/{user}")
    assert_status(200, resp, "unauthed_list_profile_sims")
    assert len(resp.data["results"]) == 1
    assert resp.data["results"][0]["model_pk"] == tester_sims[1].model_pk

    # ensure anon_before is checked.
    tester_sims[1].creation_date = ANON_BEFORE - datetime.timedelta(days=2)
    tester_sims[1].is_public = True
    tester_sims[1].save()
    resp = api_client.get(f"/api/v1/sims/{user}")
    assert_status(200, resp, "unauthed_list_profile_sims")
    assert len(resp.data["results"]) == 0

    # Check auth'ed user can view their own sims.
    api_client.force_login(user.user)
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

    # test only public sims are shown on feed page.
    api_client.logout()
    modeler_sims[0].is_public = False
    modeler_sims[0].save()
    tester_sims[1].is_public = True
    tester_sims[1].creation_date = ANON_BEFORE + datetime.timedelta(days=2)
    tester_sims[1].save()
    resp = api_client.get("/api/v1/log")
    assert_status(200, resp, "unauthed list sims")
    assert len(resp.data["results"]) == 1
    assert resp.data["results"][0]["model_pk"] == tester_sims[1].model_pk


@pytest.fixture(params=[True, False])
def viz(request, db, viz_project, pro_profile, customer_pro_by_default):
    sponsor = Profile.objects.get(user__username="sponsor")
    viz_project.sponsor = sponsor
    viz_project.is_public = request.param
    if not viz_project.is_public:
        replace_owner(viz_project, pro_profile)
    viz_project.save()
    return viz_project


@pytest.mark.django_db
class TestDeployments:
    def test_not_sponsored(self, client, viz, mock_deployments_requests_to_cluster):
        """
        For now, test unsponsored viz projects return 404.
        """
        viz.sponsor = None
        viz.save()
        resp = client.get(f"/{viz}/viz/")
        assert resp.status_code == 404

    def test_get_viz(
        self, client, api_client, viz, mock_deployments_requests_to_cluster
    ):
        resp = client.get(f"/{viz}/viz/")
        if not viz.is_public:
            assert resp.status_code == 404
            client.force_login(viz.owner.user)
            resp = client.get(f"/{viz}/viz/")

        assert resp.status_code == 200

        deployment = Deployment.objects.get(project=viz, status="creating")

        (collab,) = gen_collabs(1)
        client.force_login(collab.user)
        resp = client.get(f"/{viz}/viz/")
        if not viz.is_public:
            assert resp.status_code == 404
            viz.assign_role("read", collab.user)
            resp = client.get(f"/{viz}/viz/")

        assert resp.status_code == 200

        resp = api_client.get(f"/apps/api/v1/{viz}/deployments/{deployment.name}/")
        if not viz.is_public:
            assert resp.status_code == 404
            api_client.force_login(collab.user)
            resp = api_client.get(f"/apps/api/v1/{viz}/deployments/{deployment.name}/")
        assert resp.status_code == 200

        deployment.refresh_from_db()

        assert deployment.status == "running"

        last_load_at = deployment.last_load_at
        last_ping_at = deployment.last_ping_at
        time.sleep(0.1)

        api_client.logout()
        resp = api_client.get(f"/apps/api/v1/deployments/{deployment.pk}/")
        if not viz.is_public:
            assert resp.status_code == 404
            api_client.force_login(collab.user)
            resp = api_client.get(f"/apps/api/v1/deployments/{deployment.pk}/")

        assert resp.status_code == 200

        deployment.refresh_from_db()
        assert last_load_at < deployment.last_load_at
        assert last_ping_at < deployment.last_ping_at

        last_load_at = deployment.last_load_at
        last_ping_at = deployment.last_ping_at
        time.sleep(0.1)
        resp = client.get(f"/apps/api/v1/deployments/{deployment.pk}/?ping=True")

        assert resp.status_code == 200

        deployment.refresh_from_db()
        assert last_load_at == deployment.last_load_at
        assert last_ping_at < deployment.last_ping_at

    def test_delete_viz_deployment(
        self, client, api_client, viz, mock_deployments_requests_to_cluster
    ):
        (collab,) = gen_collabs(1)
        viz.assign_role("read", collab.user)
        client.force_login(collab.user)
        resp = client.get(f"/{viz}/viz/")
        assert resp.status_code == 200

        deployment = Deployment.objects.get(project=viz, status="creating")

        deployment.load()

        assert deployment.status == "running"

        resp = api_client.delete(f"/apps/api/v1/{viz}/deployments/{deployment.name}/")
        if viz.is_public:
            assert resp.status_code == 403  # Public returns permission denied
        else:
            assert resp.status_code == 404  # Private returns not found

        api_client.force_login(collab.user)
        resp = api_client.delete(f"/apps/api/v1/{viz}/deployments/{deployment.name}/")
        assert resp.status_code == 403  # Only has read access for project.

        deployment.refresh_from_db()
        assert deployment.status == "running"

        api_client.force_login(viz.cluster.service_account.user)
        resp = api_client.delete(f"/apps/api/v1/{viz}/deployments/{deployment.name}/")
        assert resp.status_code == 204

        deployment.refresh_from_db()
        assert deployment.status == "terminated"

        resp = api_client.get(f"/apps/api/v1/{viz}/deployments/{deployment.name}/")
        assert resp.status_code == 404

        resp = client.get(f"/{viz}/viz/")
        assert resp.status_code == 200

        assert Deployment.objects.get(project=viz, status="creating")

        assert Deployment.objects.filter(project=viz).count() == 2

    def test_get_embed(
        self, client, api_client, viz, mock_deployments_requests_to_cluster
    ):
        (collab, profile,) = gen_collabs(2)
        viz.assign_role("read", profile.user)
        resp = client.get(f"/{viz}/embed/test/")
        assert resp.status_code == 404

        # Check that viz doesn't exist.e.g. the 404 above is not just from
        # the anon user not having access to the project.
        if not viz.is_public:
            viz.assign_role("read", collab.user)
            client.force_login(collab.user)
            resp = client.get(f"/{viz}/embed/test/")
            assert resp.status_code == 404
            client.logout()

        ea = EmbedApproval.objects.create(
            project=viz, owner=profile, name="test", url="http://embed.compute.studio",
        )
        url = ea.get_absolute_url()
        resp = client.get(url)
        if not viz.is_public:
            assert resp.status_code == 404
            client.force_login(collab.user)
            resp = client.get(f"/{viz}/embed/test/")

        assert resp.status_code == 200
        assert resp._headers["content-security-policy"] == (
            "Content-Security-Policy",
            "frame-ancestors http://embed.compute.studio",
        )

        resp = client.get((f"/{viz}/embed/doesnotexist/"))
        assert resp.status_code == 404

        deployment = Deployment.objects.get(project=viz, status="creating")
        resp = client.get(f"/{viz}/viz/{ea.name}/")
        assert resp.status_code == 200

        api_client.force_login(collab.user)
        resp = api_client.get(f"/apps/api/v1/{viz}/deployments/{deployment.name}/")
        assert resp.status_code == 200

        resp = api_client.get(f"/apps/api/v1/deployments/{deployment.pk}/")
        assert resp.status_code == 200
