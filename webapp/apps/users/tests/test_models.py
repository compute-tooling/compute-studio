from django.contrib.auth import get_user_model

import pytest

from webapp.apps.users.models import Profile, Project, is_profile_active

User = get_user_model()


@pytest.mark.django_db
class TestStripeModels():

    def test_construct_user(self, stripe_customer):
        user = User.objects.create(username='tester', email='tester@email.com')
        assert user.username
        assert user.email

    def test_project(self):
        p = Project(name='test project', server_cost=36)
        assert p.server_cost_in_secs == 0.01
        assert p.n_secs_per_penny == 1.0
        assert p.run_cost(1) == 0.01
        assert p.run_cost(0.5, adjust=True) == 0.01
        assert p.run_cost(0.5, adjust=False) < 0.01
        assert p.run_cost(2) == 0.02
        assert Project.dollar_to_penny(0.01) == 1

    def test_create_profile(self, user):
        profile = Profile.create_from_user(user, True)
        assert profile
        assert profile.user == user
        assert profile.is_active == True
        assert is_profile_active(user) == True
        profile.is_active = False
        assert profile.is_active == False
        assert is_profile_active(user) == False
