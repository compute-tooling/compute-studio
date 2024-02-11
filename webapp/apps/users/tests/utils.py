import os
import pytest
import re
from contextlib import contextmanager
import secrets

from django.contrib.auth import get_user_model

import requests_mock
import stripe

from webapp.settings import USE_STRIPE
from webapp.apps.billing.models import Customer, Product, Plan
from webapp.apps.users.models import Cluster, create_profile_from_user, Profile
import webapp.apps.users.models


# # stripe.api_key = os.environ.get("STRIPE_SECRET")

User = get_user_model()


def gen_collabs(n, plan=None):
    for _ in range(n):
        key = secrets.token_hex(3)
        u = User.objects.create_user(
            f"collab-{key}", f"collab-{key}@example.com", "heyhey2222"
        )
        create_profile_from_user(u)
        profile = Profile.objects.get(user=u)
        if plan is not None and USE_STRIPE:
            stripe_customer = stripe.Customer.create(
                email=u.email, source="tok_bypassPending"
            )
            Customer.get_or_construct(stripe_customer.id, user=u)
            profile.refresh_from_db()
            product = Product.objects.get(name="Compute Studio Subscription")
            plan_instance = product.plans.get(nickname=f"Monthly {plan.title()} Plan")
            profile.user.customer.update_plan(plan_instance)
            profile.refresh_from_db()
            yield profile
        elif plan is not None:
            Customer.objects.create(
                stripe_id=f"collab-{u.pk}",
                livemode=False,
                user=u,
                default_source="123",
                metadata={},
            )
            profile.refresh_from_db()
            mock_cp = lambda: {"name": plan, "plan_duration": plan.lower()}
            profile.user.customer.current_plan = mock_cp
            yield profile
        else:
            yield profile


def replace_owner(project, new_owner):
    prev_owner = project.owner
    project.owner = new_owner
    project.save()

    current = webapp.apps.users.models.HAS_USAGE_RESTRICTIONS
    webapp.apps.users.models.HAS_USAGE_RESTRICTIONS = False

    project.assign_role(None, prev_owner.user)
    project.assign_role("admin", project.owner.user)

    webapp.apps.users.models.HAS_USAGE_RESTRICTIONS = current
