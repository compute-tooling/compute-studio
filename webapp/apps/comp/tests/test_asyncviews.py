import os
import json
import uuid

import pytest
import requests_mock

from django.contrib import auth
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from webapp.apps.billing.models import UsageRecord
from webapp.apps.users.models import Project, Profile

from webapp.apps.comp.models import Inputs, Simulation
from webapp.apps.comp.ioutils import get_ioutils
from .compute import MockCompute, MockComputeWorkerFailure


User = auth.get_user_model()


def read_outputs(outputs_name):
    curr = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(curr, f"{outputs_name}.json"), "r") as f:
        outputs = f.read()
    return outputs


def login_client(client, user, password):
    """
    Helper function to login client
    """
    success = client.login(username=user.username, password=password)
    assert success
    return success


def set_auth_token(api_client: APIClient, user: User):
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {user.auth_token.key}")


class CoreTestMixin:
    @property
    def project(self):
        if getattr(self, "_project", None) is None:
            self._project = Project.objects.get(
                owner__user__username=self.owner, title=self.title
            )
        return self._project


class RunMockModel(CoreTestMixin):
    def __init__(
        self,
        owner,
        title,
        defaults,
        inputs,
        errors_warnings,
        client,
        api_client,
        worker_url,
        comp_api_user,
        monkeypatch,
        mockcompute,
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
        with requests_mock.Mocker() as mock:
            print("mocking", f"{self.worker_url}{self.owner}/{self.title}/inputs")
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
            assert init_resp.status_code == 201
            inputs_hashid = init_resp.data["hashid"]

            get_resp_pend = self.api_client.get(
                f"/{self.owner}/{self.title}/api/v1/inputs/{inputs_hashid}/"
            )
            assert get_resp_pend.status_code == 200
            assert get_resp_pend.data["status"] == "PENDING"
            assert get_resp_pend.data["hashid"] == inputs_hashid

            edit_inputs_resp = self.client.get(
                f"/{self.owner}/{self.title}/inputs/{inputs_hashid}/"
            )
            assert edit_inputs_resp.status_code == 200

            set_auth_token(self.api_client, self.comp_api_user.user)
            self.mockcompute.client = self.api_client
            self.monkeypatch.setattr(
                "webapp.apps.comp.views.api.Compute", self.mockcompute
            )
            put_adj_resp = self.api_client.put(
                f"/inputs/api/", data=adj_callback_data, format="json"
            )
            assert put_adj_resp.status_code == 200

            inputs_hashid = get_resp_pend.data["hashid"]
            get_resp_succ = self.api_client.get(
                f"/{self.owner}/{self.title}/api/v1/inputs/{inputs_hashid}/"
            )
            assert get_resp_succ.status_code == 200
            assert get_resp_succ.data["status"] == "SUCCESS"
            assert get_resp_succ.data["sim"]["model_pk"]

            model_pk = get_resp_succ.data["sim"]["model_pk"]
            inputs = Inputs.objects.from_hashid(inputs_hashid)
            assert inputs.outputs.model_pk == model_pk
            assert inputs.outputs.status == "PENDING"

            self.mockcompute.sim = inputs.outputs
            get_resp_pend = self.api_client.get(
                f"/{self.owner}/{self.title}/api/v1/{model_pk}/"
            )
            assert get_resp_pend.status_code == 202
            sim = Simulation.objects.get(project=self.project, model_pk=model_pk)

        get_resp_succ = self.api_client.get(
            f"/{self.owner}/{self.title}/api/v1/{model_pk}/"
        )
        assert get_resp_succ.status_code == 200
        model_pk = get_resp_succ.data["model_pk"]
        sim = Simulation.objects.get(project=self.project, model_pk=model_pk)
        assert sim.status == "SUCCESS"
        assert sim.outputs
        assert sim.traceback is None

        # test get inputs form model_pk
        get_resp_inputs = self.api_client.get(
            f"/{self.owner}/{self.title}/api/v1/{model_pk}/edit/"
        )
        assert get_resp_inputs.status_code == 200
        data = get_resp_inputs.data
        assert "adjustment" in data
        assert data["sim"]["model_pk"] == model_pk
        assert data["hashid"] == inputs_hashid


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

    def test_runmodel(
        self, monkeypatch, client, api_client, profile, worker_url, comp_api_user
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
        )
        rmm.run()

    # def test_anon_perms(
    #     self, client, api_client, profile, worker_url, comp_api_user
    # ):
    #     """
    #     Test lifetime of submitting a model.
    #     """
    #     # set_auth_token(api_client, profile.user)
    #     defaults_resp_data = {"status": "SUCCESS", **self.defaults()}
    #     adj = self.inputs_ok()
    #     adj_job_id = str(uuid.uuid4())
    #     adj_resp_data = {"job_id": adj_job_id, "qlength": 1}
    #     adj_callback_data = {
    #         "status": "SUCCESS",
    #         "job_id": adj_job_id,
    #         **{"errors_warnings": self.errors_warnings()},
    #     }
    #     with requests_mock.Mocker() as mock:
    #         print("mocking", f"{worker_url}{self.owner}/{self.title}/inputs")
    #         mock.register_uri(
    #             "POST",
    #             f"{worker_url}{self.owner}/{self.title}/inputs",
    #             text=json.dumps(defaults_resp_data),
    #         )
    #         mock.register_uri(
    #             "POST",
    #             f"{worker_url}{self.owner}/{self.title}/parse",
    #             text=json.dumps(adj_resp_data),
    #         )

    #         init_resp = api_client.post(
    #             f"/{self.owner}/{self.title}/api/v1/", data=adj, format="json"
    #         )


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


def test_outputs_api(db, api_client, profile, password):
    # Test auth errors return 401.
    anon_user = auth.get_user(api_client)
    assert not anon_user.is_authenticated
    assert api_client.put("/outputs/api/").status_code == 401
    api_client.login(username=profile.user.username, password=password)
    assert api_client.put("/outputs/api/").status_code == 401

    # Test data errors return 400
    user = User.objects.get(username="comp-api-user")
    api_client.login(username=user.username, password="heyhey2222")
    assert (
        api_client.put("/outputs/api/", data={"bad": "data"}, format="json").status_code
        == 400
    )
