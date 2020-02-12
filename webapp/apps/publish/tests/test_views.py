import json
from decimal import Decimal

import pytest

from django.contrib.auth import get_user_model, get_user
from guardian.shortcuts import assign_perm, remove_perm

from webapp.apps.comp.models import Simulation
from webapp.apps.users.models import Project, Profile

from webapp.apps.publish.serializers import PublishSerializer


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
            "server_size": [4, 8],
            "listed": True,
        }
        resp = client.post("/publish/api/", post_data)
        assert resp.status_code == 401

        client.login(username="modeler", password="modeler2222")
        resp = client.post("/publish/api/", post_data)
        assert resp.status_code == 200

        project = Project.objects.get(
            title="New-Model", owner__user__username="modeler"
        )
        assert project
        assert project.server_cost

    def test_get_detail_api(self, client, test_models):
        exp = {
            "title": "Detail-Test",
            "oneliner": "oneliner",
            "description": "desc",
            "repo_url": "https://github.com/compute-tooling/compute-studio",
            "server_size": ["4", "2"],
            "exp_task_time": 20,
            "server_cost": Decimal("0.1"),
            "listed": True,
            "status": "live",
        }
        owner = Profile.objects.get(user__username="modeler")
        project = Project.objects.create(**dict(exp, **{"owner": owner}))
        resp = client.get("/publish/api/modeler/Detail-Test/detail/")
        assert resp.status_code == 200
        data = resp.json()
        data.pop("owner")
        data.pop("cluster_type")
        serializer = PublishSerializer(project, data=data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data == exp

        resp = client.get("/publish/api/moDeler/detail-test/detail/")
        assert resp.status_code == 200

    def test_put_detail_api(self, client, test_models, profile, password):
        put_data = {
            "title": "Used-for-testing",
            "oneliner": "oneliner",
            "description": "hello world!",
            "repo_url": "https://github.com/compute-tooling/compute-studio",
            "server_size": [2, 4],
        }
        # not logged in --> not authorized
        resp = client.put(
            "/publish/api/modeler/Used-for-testing/detail/",
            data=put_data,
            content_type="application/json",
        )
        assert resp.status_code == 401

        # not the owner --> not authorized
        client.login(username="sponsor", password="sponsor2222")
        resp = client.put(
            "/publish/api/Modeler/Used-FOR-testing/detail/",
            data=put_data,
            content_type="application/json",
        )
        assert resp.status_code == 401

        # logged in and owner --> do update
        client.login(username="modeler", password="modeler2222")
        resp = client.put(
            "/publish/api/modeler/Used-for-testing/detail/",
            data=put_data,
            content_type="application/json",
        )
        assert resp.status_code == 200
        project = Project.objects.get(
            title="Used-for-testing", owner__user__username="modeler"
        )
        assert project.description == put_data["description"]
        assert project.status == "updating"

        # Description can't be empty.
        resp = client.put(
            "/publish/api/modeler/Used-for-testing/detail/",
            data=dict(put_data, **{"description": None}),
            content_type="application/json",
        )
        assert resp.status_code == 400

        # test add write_project permission allows update
        put_data["description"] = "hello world!!"
        client.login(username=profile.user.username, password=password)
        resp = client.put(
            "/publish/api/modeler/Used-for-testing/detail/",
            data=put_data,
            content_type="application/json",
        )
        # make sure "tester" doesn't have access already.
        assert resp.status_code == 401

        project = Project.objects.get(
            title="Used-for-testing", owner__user__username="modeler"
        )
        assign_perm("write_project", profile.user, project)
        resp = client.put(
            "/publish/api/modeler/Used-for-testing/detail/",
            data=put_data,
            content_type="application/json",
        )
        assert resp.status_code == 200
        project = Project.objects.get(
            title="Used-for-testing", owner__user__username="modeler"
        )
        assert project.description == put_data["description"]
        remove_perm("write_project", profile.user, project)
        assert not profile.user.has_perm("write_project", project)

    def test_get_detail_page(self, client, test_models):
        resp = client.get("/modeler/Used-for-testing/detail/")
        assert resp.status_code == 200

        resp = client.get("/Modeler/used-for-testing/detail/")
        assert resp.status_code == 200

    def test_get_projects(self, client, test_models):
        resp = client.get("/publish/api/")
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
