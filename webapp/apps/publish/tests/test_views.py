import json
from decimal import Decimal

import pytest

from django.contrib.auth import get_user_model, get_user
from guardian.shortcuts import assign_perm, remove_perm

from webapp.apps.comp.models import Simulation
from webapp.apps.users.models import Project, Profile, Deployment, EmbedApproval, Tag
from webapp.apps.users.serializers import ProjectSerializer, DeploymentSerializer

from .utils import mock_sync_projects, mock_get_version
from webapp.apps.users.tests.utils import gen_collabs, replace_owner


@pytest.fixture(params=[True, False])
def visibility_params(request, db, plus_profile, project, viz_project):
    is_public = request.param
    if is_public:
        owner = Profile.objects.get(user__username="modeler")
    else:
        owner = plus_profile
        replace_owner(project, owner)
        replace_owner(viz_project, owner)

    return owner, is_public


@pytest.mark.django_db
@pytest.mark.usefixtures("customer_plus_by_default")
class TestPublishViews:
    def test_get(self, client):
        resp = client.get("/publish/")
        assert resp.status_code == 200
        resp = client.get("/new/")
        assert resp.status_code == 200

    def test_post(self, client, visibility_params):
        owner, is_public = visibility_params
        post_data = {
            "title": "New-Model",
            "oneliner": "oneliner",
            "description": "**Super** new!",
            "repo_url": "https://github.com/compute-tooling/compute-studio",
            "repo_tag": "dev",
            "cpu": 3,
            "memory": 9,
            "listed": True,
            "is_public": is_public,
        }
        with mock_sync_projects():
            resp = client.post("/apps/api/v1/", post_data)
        assert resp.status_code == 401

        client.force_login(owner.user)

        with mock_sync_projects():
            resp = client.post("/apps/api/v1/", post_data)
        assert resp.status_code == 200

        project = Project.objects.get(title="New-Model", owner=owner)
        assert project
        assert project.server_cost

        api_user = Profile.objects.get(user__username="comp-api-user")
        assert project.has_write_access(api_user.user)
        assert project.role(api_user.user) == "write"
        assert project.role(project.cluster.service_account.user) == "write"
        assert project.role(project.owner.user) == "admin"

        client.logout()
        resp = client.get(f"/{owner}/New-Model/")
        if is_public:
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        else:
            assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    def test_get_detail_api(self, api_client, client, visibility_params):
        owner, is_public = visibility_params
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
            "tech": "python-paramtools",
            "callable_name": None,
            "is_public": is_public,
        }
        project = Project.objects.create(**dict(exp, **{"owner": owner}))
        project.assign_role("admin", owner.user)
        project.owner = owner  # Necessary for mock customer attribute on owner.
        for url in [
            f"/apps/api/v1/{owner}/Detail-Test/",
            f"/apps/api/v1/{str(owner).upper()}/detail-test/",
        ]:
            api_client.logout()
            resp = api_client.get(url)
            if is_public:
                assert (
                    resp.status_code == 200
                ), f"Expected 200, got {resp.status_code} {resp.url}"
            else:
                assert (
                    resp.status_code == 404
                ), f"Expected 404, got {resp.status_code} {resp.url}"
                api_client.force_login(owner.user)
                resp = api_client.get(url)
                assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_put_detail_api(
        self, client, api_client, test_models, password, visibility_params,
    ):
        owner, is_public = visibility_params
        put_data = {
            "title": "Used-for-testing",
            "oneliner": "oneliner",
            "description": "hello world!",
            "repo_url": "https://github.com/compute-tooling/compute-studio",
            "repo_tag": "dev",
            "cpu": 2,
            "memory": 6,
            "lastet_tag": "v2",
            "is_public": is_public,
        }
        project = Project.objects.get(owner=owner, title="Used-for-testing")
        project.is_public = is_public
        project.save()

        # not logged in --> not authorized
        resp = api_client.put(
            f"/apps/api/v1/{owner}/Used-for-testing/",
            data=put_data,
            content_type="application/json",
        )
        assert resp.status_code == 401

        # not the owner --> not authorized
        client.login(username="sponsor", password="sponsor2222")
        resp = client.put(
            f"/apps/api/v1/{owner}/Used-FOR-testing/",
            data=put_data,
            content_type="application/json",
        )
        exp_notauthed_code = 403 if is_public else 404
        assert resp.status_code == exp_notauthed_code

        # logged in and owner --> do update
        client.force_login(owner.user)
        with mock_sync_projects():
            resp = client.put(
                f"/apps/api/v1/{owner}/Used-for-testing/",
                data=put_data,
                content_type="application/json",
            )
        assert resp.status_code == 200
        project = Project.objects.get(title="Used-for-testing", owner=owner)
        assert project.description == put_data["description"]
        assert project.status == "live"

        # Description can't be empty.
        resp = client.put(
            f"/apps/api/v1/{owner}/Used-for-testing/",
            data=dict(put_data, **{"description": None}),
            content_type="application/json",
        )
        assert resp.status_code == 400

        # test add write_project permission allows update
        put_data["description"] = "hello world!!"
        (collab,) = gen_collabs(1)
        client.force_login(collab.user)
        with mock_sync_projects():
            resp = client.put(
                f"/apps/api/v1/{owner}/Used-for-testing/",
                data=put_data,
                content_type="application/json",
            )
        # make sure "tester" doesn't have access already.
        assert resp.status_code == exp_notauthed_code

        project = Project.objects.get(title="Used-for-testing", owner=owner)
        project.assign_role("write", collab.user)
        with mock_sync_projects():
            resp = client.put(
                f"/apps/api/v1/{owner}/Used-for-testing/",
                data=put_data,
                content_type="application/json",
            )
        assert resp.status_code == 200
        project = Project.objects.get(title="Used-for-testing", owner=owner)
        assert project.description == put_data["description"]

    def test_get_detail_page(self, client, visibility_params):
        owner, is_public = visibility_params
        project = Project.objects.get(owner=owner, title="Used-for-testing")
        project.is_public = is_public
        project.save()
        for url in [
            f"/{owner}/Used-for-testing/",
            f"/{str(owner).upper()}/used-for-testing/",
        ]:
            client.logout()
            resp = client.get(url)
            if is_public:
                assert (
                    resp.status_code == 200
                ), f"Expected 200, got {resp.status_code} {resp.url}"
            else:
                assert (
                    resp.status_code == 404
                ), f"Expected 404, got {resp.status_code} {resp.url}"
                client.force_login(project.owner.user)
                resp = client.get(url)
                assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_get_projects(self, api_client):
        resp = api_client.get("/apps/api/v1/")
        assert resp.status_code == 200
        exp = set(proj.title for proj in Project.objects.all())
        act = set(proj["title"] for proj in resp.data)
        assert exp == act

    def test_get_private_projects(self, api_client, plus_profile):
        project = Project.objects.get(title="Used-for-testing")
        project.is_public = False
        project.owner = plus_profile
        replace_owner(project, plus_profile)
        project.save()

        # Test private app not included in unauthenticated get
        resp = api_client.get("/apps/api/v1/")
        assert resp.status_code == 200
        exp = set(proj.title for proj in Project.objects.filter(is_public=True).all())
        act = set(proj["title"] for proj in resp.data)
        assert exp == act

        # Test private app not included if user doesn't have write access
        collab = next(gen_collabs(1))
        api_client.force_login(collab.user)
        resp = api_client.get("/apps/api/v1/")
        assert resp.status_code == 200
        exp = set(proj.title for proj in Project.objects.filter(is_public=True).all())
        act = set(proj["title"] for proj in resp.data)
        assert exp == act

        # Test private app included if user has read access
        api_client.force_login(project.owner.user)
        resp = api_client.get("/apps/api/v1/")
        assert resp.status_code == 200
        exp = set(proj.title for proj in Project.objects.all())
        act = set(proj["title"] for proj in resp.data)
        assert exp == act

        api_client.force_login(collab.user)
        project.assign_role("read", collab.user)
        resp = api_client.get("/apps/api/v1/")
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

        # test unauth'ed get on profile endpoint only returns public
        # projects and sets sim_count and user_count to None.
        project.listed = True
        project.is_public = False
        project.save()

        modeler = test_models[0].project.owner

        with mock_get_version():
            resp = api_client.get("/api/v1/models/modeler")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        exp = set(
            proj.title for proj in Project.objects.filter(owner=modeler, is_public=True)
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

    def test_tags_api(self, api_client, test_models, visibility_params):
        owner, is_public = visibility_params
        prof = Profile.objects.get(user__username="comp-api-user")
        api_client.force_login(prof.user)

        project = test_models[0].project
        project.is_public = is_public
        project.save()
        assert project.has_write_access(prof.user)

        resp = api_client.post(
            f"/apps/api/v1/{project.owner}/{project.title}/tags/",
            data={"latest_tag": "v5"},
            format="json",
        )

        assert resp.status_code == 200
        project.refresh_from_db()
        assert project.latest_tag == Tag.objects.get(project=project, image_tag="v5")

        resp = api_client.post(
            f"/apps/api/v1/{project.owner}/{project.title}/tags/",
            data={"staging_tag": "v6"},
            format="json",
        )

        assert resp.status_code == 200
        project.refresh_from_db()
        assert project.staging_tag == Tag.objects.get(project=project, image_tag="v6")
        assert project.latest_tag == Tag.objects.get(project=project, image_tag="v5")

        resp = api_client.post(
            f"/apps/api/v1/{project.owner}/{project.title}/tags/",
            data={"latest_tag": "v6", "staging_tag": None},
            format="json",
        )

        assert resp.status_code == 200
        project.refresh_from_db()
        assert project.staging_tag is None
        assert project.latest_tag == Tag.objects.get(project=project, image_tag="v6")

        resp = api_client.post(
            f"/apps/api/v1/{project.owner}/{project.title}/tags/",
            data={},
            format="json",
        )

        assert resp.status_code == 400
        project.refresh_from_db()
        assert project.staging_tag is None
        assert project.latest_tag == Tag.objects.get(project=project, image_tag="v6")

    def test_private_app_restrictions(self, api_client):
        post_data = {
            "title": "New-Model",
            "oneliner": "oneliner",
            "description": "**Super** new!",
            "repo_url": "https://github.com/compute-tooling/compute-studio",
            "repo_tag": "dev",
            "cpu": 3,
            "memory": 9,
            "listed": True,
            "is_public": False,
        }

        (free_user,) = gen_collabs(1)
        api_client.force_login(free_user.user)
        with mock_sync_projects():
            resp = api_client.post("/apps/api/v1/", post_data)
        assert resp.status_code == 400
        data = resp.json()
        assert "make_private" == data["collaborators"]["test_name"]

        with pytest.raises(Project.DoesNotExist):
            Project.objects.get(title="New-Model")

        post_data["is_public"] = True
        with mock_sync_projects():
            resp = api_client.post("/apps/api/v1/", post_data)
        assert resp.status_code == 200

        with mock_sync_projects():
            resp = api_client.put(
                f"/apps/api/v1/{free_user}/New-Model/", {"is_public": False},
            )
        assert resp.status_code == 400
        data = resp.json()
        assert "make_private" == data["collaborators"]["test_name"]


class TestDeployments:
    def test_list_deployments(
        self, db, client, api_client, viz_project, mock_deployments_requests_to_cluster
    ):
        viz_project.sponsor = viz_project.owner
        viz_project.save()

        resp = client.get(f"/{viz_project}/viz/")
        assert resp.status_code == 200

        resp = api_client.get(f"/apps/api/v1/deployments/")
        assert resp.status_code == 403

        (collab,) = gen_collabs(1)
        api_client.force_login(collab.user)
        resp = api_client.get(f"/apps/api/v1/deployments/")
        assert resp.status_code == 200
        assert resp.json()["results"] == []

        api_client.force_login(viz_project.cluster.service_account.user)
        resp = api_client.get(f"/apps/api/v1/deployments/")
        assert resp.status_code == 200
        assert (
            resp.json()["results"]
            == DeploymentSerializer(
                Deployment.objects.filter(project=viz_project), many=True
            ).data
        )


@pytest.mark.django_db
class TestEmbedApprovalAPI:
    def test_create_embed_approval(self, api_client, project, visibility_params):
        owner, is_public = visibility_params
        project.is_public = is_public
        project.save()

        free_profile = Profile.objects.get(user__username="hdoupe")

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

        if is_public:
            resp = api_client.post(
                base, data={"name": "test", "url": "example.com"}, format="json"
            )
            assert resp.status_code == 400
        else:
            resp = api_client.post(
                base, data={"name": "test", "url": "example.com"}, format="json"
            )
            assert resp.status_code == 404
            project.assign_role("read", free_profile.user)
            resp = api_client.post(
                base, data={"name": "test", "url": "example.com"}, format="json"
            )
            assert resp.status_code == 400

        assert "ParamTools" in resp.json()["tech"]

        project.tech = "dash"
        project.save()

        if is_public:
            resp = api_client.post(
                base, data={"name": "test", "url": "example.com"}, format="json"
            )
            assert resp.status_code == 200
        else:
            project.assign_role(None, free_profile.user)
            resp = api_client.post(
                base, data={"name": "test", "url": "example.com"}, format="json"
            )
            assert resp.status_code == 404
            project.assign_role("read", free_profile.user)
            resp = api_client.post(
                base, data={"name": "test", "url": "example.com"}, format="json"
            )
            assert resp.status_code == 200

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
