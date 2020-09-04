import json
from decimal import Decimal

import pytest

from django.contrib.auth import get_user_model, get_user
from guardian.shortcuts import assign_perm, remove_perm

from webapp.apps.comp.models import Simulation
from webapp.apps.users.models import Project, Profile, EmbedApproval
from webapp.apps.users.serializers import ProjectSerializer

from .utils import mock_sync_projects, mock_get_version


@pytest.mark.django_db
class TestPublishViews:
    def test_get(self, client):
        resp = client.get("/publish/")
        assert resp.status_code == 200

    def test_post(self, client):
        post_data = {
            "title": "New-Model",
            "oneliner": "oneliner",
            "description": "**Super** new!",
            "repo_url": "https://github.com/compute-tooling/compute-studio",
            "repo_tag": "dev",
            "cpu": 3,
            "memory": 9,
            "listed": True,
            "latest_tag": "v1",
        }
        with mock_sync_projects():
            resp = client.post("/apps/api/v1/", post_data)
        assert resp.status_code == 401

        client.login(username="modeler", password="modeler2222")
        with mock_sync_projects():
            resp = client.post("/apps/api/v1/", post_data)
        assert resp.status_code == 200

        project = Project.objects.get(
            title="New-Model", owner__user__username="modeler"
        )
        assert project
        assert project.server_cost

        api_user = Profile.objects.get(user__username="comp-api-user")
        assert project.has_write_access(api_user.user)

    def test_get_detail_api(self, api_client, client, test_models):
        exp = {
            "title": "Detail-Test",
            "oneliner": "oneliner",
            "description": "desc",
            "repo_url": "https://github.com/compute-tooling/compute-studio",
            "repo_tag": "master",
            "cpu": 2,
            "memory": 6,
            "exp_task_time": 20,
            "listed": True,
            "status": "live",
            "latest_tag": "v1",
            "tech": "python-paramtools",
            "callable_name": None,
        }
        owner = Profile.objects.get(user__username="modeler")
        project = Project.objects.create(**dict(exp, **{"owner": owner}))
        resp = client.get("/apps/api/v1/modeler/Detail-Test/detail/")
        assert resp.status_code == 200
        data = resp.json()
        data.pop("owner")
        data.pop("cluster_type")
        serializer = ProjectSerializer(project, data=data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data == exp
        assert serializer.data["has_write_access"] == False

        resp = client.get("/apps/api/v1/moDeler/detail-test/detail/")
        assert resp.status_code == 200

        api_client.force_login(owner.user)
        resp = api_client.get("/apps/api/v1/moDeler/detail-test/detail/")
        assert resp.data["has_write_access"] == True

    def test_put_detail_api(self, client, test_models, profile, password):
        put_data = {
            "title": "Used-for-testing",
            "oneliner": "oneliner",
            "description": "hello world!",
            "repo_url": "https://github.com/compute-tooling/compute-studio",
            "repo_tag": "dev",
            "cpu": 2,
            "memory": 6,
            "lastet_tag": "v2",
        }
        # not logged in --> not authorized
        resp = client.put(
            "/apps/api/v1/modeler/Used-for-testing/detail/",
            data=put_data,
            content_type="application/json",
        )
        assert resp.status_code == 401

        # not the owner --> not authorized
        client.login(username="sponsor", password="sponsor2222")
        resp = client.put(
            "/apps/api/v1/Modeler/Used-FOR-testing/detail/",
            data=put_data,
            content_type="application/json",
        )
        assert resp.status_code == 401

        # logged in and owner --> do update
        client.login(username="modeler", password="modeler2222")
        with mock_sync_projects():
            resp = client.put(
                "/apps/api/v1/modeler/Used-for-testing/detail/",
                data=put_data,
                content_type="application/json",
            )
        assert resp.status_code == 200
        project = Project.objects.get(
            title="Used-for-testing", owner__user__username="modeler"
        )
        assert project.description == put_data["description"]
        assert project.status == "live"

        # Description can't be empty.
        resp = client.put(
            "/apps/api/v1/modeler/Used-for-testing/detail/",
            data=dict(put_data, **{"description": None}),
            content_type="application/json",
        )
        assert resp.status_code == 400

        # test add write_project permission allows update
        put_data["description"] = "hello world!!"
        client.login(username=profile.user.username, password=password)
        resp = client.put(
            "/apps/api/v1/modeler/Used-for-testing/detail/",
            data=put_data,
            content_type="application/json",
        )
        # make sure "tester" doesn't have access already.
        assert resp.status_code == 401

        project = Project.objects.get(
            title="Used-for-testing", owner__user__username="modeler"
        )
        assign_perm("write_project", profile.user, project)
        with mock_sync_projects():
            resp = client.put(
                "/apps/api/v1/modeler/Used-for-testing/detail/",
                data=put_data,
                content_type="application/json",
            )
        assert resp.status_code == 200
        project = Project.objects.get(
            title="Used-for-testing", owner__user__username="modeler"
        )
        assert project.description == put_data["description"]

    def test_get_detail_page(self, client, test_models):
        resp = client.get("/modeler/Used-for-testing/detail/")
        assert resp.status_code == 200

        resp = client.get("/Modeler/used-for-testing/detail/")
        assert resp.status_code == 200

    def test_get_projects(self, client, test_models):
        resp = client.get("/apps/api/v1/")
        assert resp.status_code == 200

        exp = set(proj.title for proj in Project.objects.all())
        act = set(proj["title"] for proj in resp.data)

        assert exp == act

    def test_models_api(self, api_client, test_models):
        # test unauth'ed get returns 403
        resp = api_client.get("/api/v1/models")
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

        # test unauth'ed get on profile endpoint only returns listed
        # projects and sets sim_count and user_count to None.
        project = Project.objects.get(title="Used-for-testing")
        project.listed = False
        project.save()

        modeler = test_models[0].project.owner

        with mock_get_version():
            resp = api_client.get("/api/v1/models/modeler")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        exp = set(
            proj.title for proj in Project.objects.filter(owner=modeler, listed=True)
        )
        act = set(proj["title"] for proj in resp.data["results"])
        assert exp == act
        assert all(
            "user_count" not in project and "sim_count" not in project
            for project in resp.data["results"]
        )

        project = Project.objects.get(title="Used-for-testing")
        project.listed = False
        project.save()

        # test auth'ed get returns all projects.
        modeler = test_models[0].owner
        api_client.force_login(modeler.user)
        with mock_get_version():
            resp = api_client.get("/api/v1/models")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

        exp = set(proj.title for proj in Project.objects.filter(owner=modeler))
        act = set(proj["title"] for proj in resp.data["results"])
        assert exp == act

    def test_recent_models_api(self, api_client, test_models, profile):
        # test unauth'ed get returns 403
        resp = api_client.get("/api/v1/models/recent/")
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

        # test auth'ed user gets same result as recent_sims
        user = test_models[0].owner.user
        api_client.force_login(user)
        resp = api_client.get("/api/v1/models/recent/")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

        exp = [
            project.title for project in test_models[0].owner.recent_models(limit=10)
        ]
        act = [project["title"] for project in resp.data["results"]]
        assert exp == act

        # test auth'ed user cannot view other project's private data.
        Simulation.objects.fork(test_models[0], profile.user)
        api_client.force_login(profile.user)
        resp = api_client.get("/api/v1/models/recent/")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

        for project in resp.data["results"]:
            p = Project.objects.get(
                title=project["title"], owner__user__username=project["owner"]
            )
            if p.has_write_access(profile.user):
                assert "sim_count" in project and "user_count" in project
            else:
                assert "sim_count" not in project and "user_count" not in project

    def test_deployments_api(self, api_client, test_models):
        prof = Profile.objects.get(user__username="comp-api-user")
        api_client.force_login(prof.user)

        project = test_models[0].project
        assert project.has_write_access(prof.user)

        resp = api_client.post(
            f"/apps/api/v1/{project.owner}/{project.title}/tags/",
            data={"latest_tag": "v5"},
            format="json",
        )

        assert resp.status_code == 200
        project.refresh_from_db()
        assert project.latest_tag == "v5"


@pytest.mark.django_db
class TestEmbedApprovalAPI:
    def test_create_embed_approval(self, api_client, project, free_profile):
        base = f"/apps/api/v1/{project.owner}/{project.title}/embedapprovals/"
        resp = api_client.post(
            base, data={"name": "deny", "url": "example.com"}, format="json"
        )
        assert resp.status_code == 403

        api_client.force_login(free_profile.user)
        resp = api_client.post(
            "/apps/api/doesnot/exist/embedapprovals/",
            data={"name": "deny", "url": "example.com"},
            format="json",
        )
        assert resp.status_code == 404

        resp = api_client.post(
            base, data={"name": "test", "url": "example.com"}, format="json"
        )
        assert resp.status_code == 400
        assert "ParamTools" in resp.json()["tech"]

        project.tech = "dash"
        project.save()
        resp = api_client.post(
            base, data={"name": "test", "url": "example.com"}, format="json"
        )
        assert resp.status_code == 200, resp.json()
        assert EmbedApproval.objects.get(
            project=project, owner=free_profile, name="test"
        )

        resp = api_client.post(
            base, data={"name": "test", "url": "example.com"}, format="json"
        )
        assert resp.status_code == 400
        assert "exists" in resp.json()

    def test_update_embed_approval(self, api_client, project, free_profile):
        base = f"/apps/api/v1/{project.owner}/{project.title}/embedapprovals/test/"

        ea = EmbedApproval.objects.create(
            project=project, owner=free_profile, name="test", url="example.com",
        )

        resp = api_client.put(base, data={"name": "test2"}, format="json")
        assert resp.status_code == 403
        resp = api_client.delete(base)
        assert resp.status_code == 403

        api_client.force_login(project.owner.user)
        resp = api_client.delete(base)
        assert resp.status_code == 404

        api_client.force_login(free_profile.user)
        resp = api_client.put(
            base, data={"name": "test2", "url": "example.com"}, format="json"
        )
        assert resp.status_code == 200, resp.json()
        ea.refresh_from_db()
        assert ea.name == "test2"

        resp = api_client.delete(
            f"/apps/api/v1/{project.owner}/{project.title}/embedapprovals/test2/"
        )
        assert resp.status_code == 204
        assert (
            EmbedApproval.objects.filter(project=project, owner=free_profile).count()
            == 0
        )

    def test_list_embed_approval(self, api_client, project, free_profile):
        base = f"/apps/api/v1/{project.owner}/{project.title}/embedapprovals/"

        for i in range(5):
            EmbedApproval.objects.create(
                project=project,
                owner=free_profile,
                name=f"test-{i}",
                url="example.com",
            )

        for i in range(2):
            EmbedApproval.objects.create(
                project=project,
                owner=project.owner,
                name=f"test2-{i}",
                url="example.com",
            )

        base = f"/apps/api/v1/{project.owner}/{project.title}/embedapprovals/"
        resp = api_client.get(base)
        assert resp.status_code == 403

        api_client.force_login(free_profile.user)
        resp = api_client.get(base)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5
        assert all(ea["owner"] == str(free_profile) for ea in data)

        api_client.force_login(project.owner.user)
        resp = api_client.get(base)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all(ea["owner"] == str(project.owner) for ea in data)
