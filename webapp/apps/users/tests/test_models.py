import datetime

import pytest

from django.contrib.auth import get_user_model
from guardian.shortcuts import assign_perm, remove_perm

from webapp.apps.billing.models import Customer
from webapp.apps.users.models import Profile, Project, is_profile_active
from webapp.apps.comp.models import Simulation, ANON_BEFORE

User = get_user_model()


@pytest.mark.django_db
class TestUserModels:
    def test_construct_user(self):
        user = User.objects.create(username="tester", email="tester@email.com")
        assert user.username
        assert user.email

    def test_project(self):
        markdown = "[hello](www.world.com)"
        p = Project(title="test project", server_cost=36, description=markdown)
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

    def test_project_access(self, profile):
        project = Project.objects.get(
            title="Used-for-testing", owner__user__username="modeler"
        )
        assert not profile.user.has_perm("write_project")
        assign_perm("write_project", profile.user, project)
        assert profile.user.has_perm("write_project", project)
        remove_perm("write_project", profile.user, project)
        assert not profile.user.has_perm("write_project", project)

    def test_recent_models(self, profile, test_models):

        assert profile.recent_models(limit=10) == [
            test_models[0].project,
            test_models[1].project,
        ]

        Simulation.objects.fork(test_models[1], profile.user)

        assert profile.recent_models(limit=10) == [
            test_models[1].project,
            test_models[0].project,
        ]

        assert profile.recent_models(limit=1) == [test_models[1].project]
