import datetime

import pytest

from django.contrib.auth import get_user_model
from guardian.shortcuts import assign_perm, remove_perm, get_perms, get_users_with_perms


from webapp.apps.billing.models import Customer
from webapp.apps.users.models import (
    Profile,
    Project,
    is_profile_active,
    Deployment,
    DeploymentException,
    EmbedApproval,
)
from webapp.apps.users.exceptions import ResourceLimitException
from webapp.apps.users.tests.utils import gen_collabs, replace_owner
from webapp.apps.comp.models import Simulation, ANON_BEFORE

User = get_user_model()


@pytest.mark.django_db
class TestUserModels:
    def test_construct_user(self):
        user = User.objects.create(username="tester", email="tester@email.com")
        assert user.username
        assert user.email

    def test_project(self, monkeypatch):
        monkeypatch.setattr(
            "webapp.apps.users.models.COMPUTE_PRICING", {"cpu": 12, "memory": 2}
        )
        markdown = "[hello](www.world.com)"
        p = Project(title="test project", description=markdown)
        assert p.server_cost_in_secs == 0.01
        assert p.n_secs_per_penny == 1.0
        assert p.run_cost(1) == 0.01
        assert p.run_cost(0.5, adjust=True) == 0.01
        assert p.run_cost(0.5, adjust=False) < 0.01
        assert p.run_cost(2) == 0.02
        assert Project.dollar_to_penny(0.01) == 1
        assert p.safe_description

    def test_create_profile(self, user):
        profile = Profile.objects.create(user=user, is_active=True)
        assert profile
        assert profile.user == user
        assert profile.is_active == True
        assert is_profile_active(user) == True
        profile.is_active = False
        assert profile.is_active == False
        assert is_profile_active(user) == False

    def test_profile_costs(self, test_models, profile):
        """See conftest for initial values in test_models"""
        assert profile.costs_breakdown() == {"February 2019": 1.0}

    def test_project_show_sponsor(self, test_models):
        """See conftest for initial values in test_models."""
        reg, sponsored = test_models
        assert reg.project.display_sponsor == "Not sponsored"
        assert sponsored.project.display_sponsor == "sponsor"

    def test_project_is_sponsored(self, test_models):
        reg, sponsored = test_models
        assert not reg.project.is_sponsored
        assert sponsored.project.is_sponsored

    def test_project_can_run(self, profile, test_models):
        reg, sponsored = test_models

        # profile has no customer:
        customer = getattr(profile.user, "customer", None)
        profile.user.customer = None
        assert not profile.can_run(reg.project)
        assert profile.can_run(sponsored.project)

        # profile has a customer.
        if customer is None:
            customer = Customer.objects.create(
                stripe_id="hello world",
                livemode=False,
                user=profile.user,
                account_balance=0,
                currency="usd",
                delinquent=False,
                default_source="123",
                metadata={},
            )

        profile.user.customer = customer  # dummy to fool method.
        assert profile.can_run(reg.project)
        assert profile.can_run(sponsored.project)

        # profile is inactive:
        profile.is_active = False
        assert not profile.can_run(reg.project)
        assert not profile.can_run(sponsored.project)

    def test_recent_models(self, profile, test_models):
        assert profile.recent_models(limit=10) == [
            test_models[0].project,
            test_models[1].project,
        ]

        test_models[1].is_public = True
        test_models[1].save()
        Simulation.objects.fork(test_models[1], profile.user)

        assert profile.recent_models(limit=10) == [
            test_models[1].project,
            test_models[0].project,
        ]

        assert profile.recent_models(limit=1) == [test_models[1].project]


class TestProjectPermissionse:
    def test_project_access(self, profile):
        project = Project.objects.get(
            title="Used-for-testing", owner__user__username="modeler"
        )
        assert not profile.user.has_perm("write_project")
        assign_perm("write_project", profile.user, project)
        assert profile.user.has_perm("write_project", project)
        remove_perm("write_project", profile.user, project)
        assert not profile.user.has_perm("write_project", project)

    def test_project_permissions(self, db, project, pro_profile):
        collab = next(gen_collabs(1))
        project.is_public = False
        replace_owner(project, pro_profile)

        # check permissions for owner and random profile
        assert get_perms(project.owner.user, project) == ["admin_project"]
        assert project.role(project.owner.user) == "admin"
        assert get_perms(collab.user, project) == []
        assert project.role(collab.user) is None

        # project owner has all levels of access
        assert (
            project.is_owner(project.owner.user)
            and project.has_admin_access(project.owner.user)
            and project.has_write_access(project.owner.user)
            and project.has_read_access(project.owner.user)
        )
        # random user has no access
        assert (
            not project.is_owner(collab.user)
            and not project.has_admin_access(collab.user)
            and not project.has_write_access(collab.user)
            and not project.has_read_access(collab.user)
        )
        # None has no access and does not cause errors
        assert (
            not project.is_owner(None)
            and not project.has_admin_access(None)
            and not project.has_write_access(None)
            and not project.has_read_access(None)
        )

        # test grant/removal of read access.
        project.grant_read_permissions(collab.user)
        assert (
            get_perms(collab.user, project) == ["read_project"]
            and project.role(collab.user) == "read"
        )
        assert (
            not project.is_owner(collab.user)
            and not project.has_admin_access(collab.user)
            and not project.has_write_access(collab.user)
            and project.has_read_access(collab.user)
        )
        project.remove_permissions(collab.user)
        assert (
            get_perms(collab.user, project) == [] and project.role(collab.user) is None
        )
        assert (
            not project.is_owner(collab.user)
            and not project.has_admin_access(collab.user)
            and not project.has_write_access(collab.user)
            and not project.has_read_access(collab.user)
        )

        # test grant/remove are idempotent:
        for _ in range(3):
            project.grant_read_permissions(collab.user)
            assert project.has_read_access(collab.user)
        for _ in range(3):
            project.remove_permissions(collab.user)
            assert not project.has_read_access(collab.user)

        # test that only one permission is applied at a time.
        project.grant_read_permissions(collab.user)
        assert get_perms(collab.user, project) == ["read_project"]
        project.grant_write_permissions(collab.user)
        assert get_perms(collab.user, project) == ["write_project"]
        project.grant_admin_permissions(collab.user)
        assert get_perms(collab.user, project) == ["admin_project"]

        project.is_public = True
        project.save()
        assert project.has_read_access(pro_profile.user)
        assert project.has_read_access(collab.user)
        assert project.has_read_access(None) is True

        # test role
        project.is_public = False
        project.save()
        project.assign_role("admin", collab.user)
        assert (
            project.has_admin_access(collab.user)
            and project.role(collab.user) == "admin"
        )
        project.assign_role("write", collab.user)
        assert (
            project.has_write_access(collab.user)
            and project.role(collab.user) == "write"
        )
        project.assign_role("read", collab.user)
        assert (
            project.has_read_access(collab.user) and project.role(collab.user) == "read"
        )
        project.assign_role(None, collab.user)
        assert (
            not project.has_read_access(collab.user)
            and project.role(collab.user) == None
        )

        with pytest.raises(ValueError):
            project.assign_role("dne", collab.user)


class TestDeployments:
    def test_create_deployment_with_ea(self, db, profile, mock_post_to_cluster):
        project = Project.objects.get(title="Test-Viz")

        ea = EmbedApproval.objects.create(
            project=project,
            owner=profile,
            url="https://embed.compute.studio",
            name="my-test-embed",
        )

        deployment, created = Deployment.objects.get_or_create_deployment(
            project=project, name="my-deployment", owner=None, embed_approval=ea,
        )

        assert created
        assert deployment.embed_approval == ea
        assert deployment.owner is None

    def test_create_deployment_with_sponsored_project(
        self, db, profile, mock_post_to_cluster
    ):
        project = Project.objects.get(title="Test-Viz")
        sponsor = Profile.objects.get(user__username="sponsor")
        project.sponsor = sponsor
        project.save()

        deployment, created = Deployment.objects.get_or_create_deployment(
            project=project, name="my-deployment", owner=None, embed_approval=None,
        )

        assert created
        assert deployment.embed_approval is None
        assert deployment.owner == sponsor

    def test_create_deployment_exception(self, db, profile, mock_post_to_cluster):
        project = Project.objects.get(title="Test-Viz")
        project.save()

        with pytest.raises(DeploymentException):
            Deployment.objects.get_or_create_deployment(
                project=project, name="my-deployment", owner=None, embed_approval=None,
            )


class TestCollaborators:
    """
    Test plan restrictions regarding making apps private and adding
    collaborators to private apps.

    Related: webapp/apps/comp/tests/test_models.py::TestCollaborators
    """

    def test_free_tier(self, db, project, free_profile):
        """
        Test private app can not have any collaborators but
        public is unlimited.
        """
        project.is_public = False
        replace_owner(project, free_profile)

        collabs = list(gen_collabs(3))

        # Test cannot add collaborator when app is private.
        with pytest.raises(ResourceLimitException) as excinfo:
            project.assign_role("read", collabs[0].user)

        assert excinfo.value.todict() == {
            "upgrade_to": "pro",
            "resource": "collaborators",
            "test_name": "add_collaborator",
            "msg": ResourceLimitException.collaborators_msg,
        }
        assert (
            get_perms(collabs[0].user, project) == []
            and project.role(collabs[1].user) == None
        )

        # Unable for free users to make apps private.
        with pytest.raises(ResourceLimitException):
            project.make_private_test()

        # Test no limit on collaborators when app is public.
        project.is_public = True
        project.save()

        for collab in collabs:
            project.assign_role("read", collab.user)
            assert (
                get_perms(collab.user, project) == ["read_project"]
                and project.role(collab.user) == "read"
            )

        with pytest.raises(ResourceLimitException):
            project.make_private_test()

    def test_pro_tier(self, db, project, pro_profile, profile):
        """
        Test able to add more than three collaborators with a private
        and public app.
        """
        project.is_public = False
        replace_owner(project, pro_profile)

        collabs = list(gen_collabs(4))

        for collab in collabs:
            project.assign_role("read", collab.user)
            assert (
                get_perms(collab.user, project) == ["read_project"]
                and project.role(collab.user) == "read"
            )

        # OK making app private.
        project.make_private_test()

        project.is_public = True
        project.save()

        for collab in collabs:
            project.assign_role(None, collab.user)
            assert project.role(collab.user) == None

        for collab in collabs:
            project.assign_role("read", collab.user)
            assert (
                get_perms(collab.user, project) == ["read_project"]
                and project.role(collab.user) == "read"
            )

        # OK making app private.
        project.make_private_test()
