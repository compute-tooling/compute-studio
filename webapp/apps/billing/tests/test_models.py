import math
import os
from datetime import datetime

from django.contrib.auth import get_user_model

import pytest
import stripe

from webapp.apps.users.models import Profile, Project
from webapp.apps.publish.tests.utils import mock_sync_projects
from webapp.apps.billing.models import (
    Customer,
    Plan,
    Product,
    Subscription,
    SubscriptionItem,
    create_pro_billing_objects,
    UpdateStatus,
)

User = get_user_model()
stripe.api_key = os.environ.get("STRIPE_SECRET")


@pytest.mark.django_db
@pytest.mark.requires_stripe
class TestStripeModels:
    def test_construct_customer(self, stripe_customer, user):
        stripe_customer = Customer.get_stripe_object(stripe_customer.id)
        assert stripe_customer
        assert not stripe_customer.livemode

        customer, created = Customer.get_or_construct(stripe_customer.id, user)
        assert customer
        assert customer.user
        assert created
        assert not customer.livemode
        assert customer.current_plan(as_dict=False).plan == Plan.objects.get(
            nickname="Free Plan"
        )

        customer, created = Customer.get_or_construct(stripe_customer.id)
        assert customer
        assert customer.user
        assert not created
        assert not customer.livemode

    def test_update_customer(self, customer):
        tok = "tok_bypassPending"
        prev_source = customer.default_source
        customer.update_source(tok)
        assert customer.default_source != prev_source

    def test_cancel_subscriptions(self, pro_profile):
        customer = pro_profile.user.customer
        for sub in customer.subscriptions.all():
            assert not sub.cancel_at_period_end
        customer.cancel_subscriptions()
        for sub in customer.subscriptions.all():
            assert sub.cancel_at_period_end

    def test_create_pro_billing_objects(self, db):
        # this function is called in conftest.py
        # create_pro_billing_objects()

        pro_product = Product.objects.get(name="Compute Studio Subscription")

        plans = set(
            [
                Plan.objects.get(nickname="Free Plan"),
                Plan.objects.get(nickname="Monthly Plus Plan"),
                Plan.objects.get(nickname="Yearly Plus Plan"),
                Plan.objects.get(nickname="Monthly Pro Plan"),
                Plan.objects.get(nickname="Yearly Pro Plan"),
            ]
        )

        assert set(pro_product.plans.all()) == plans

    def test_customer_card_info(self, db, customer):
        # As of today, 3/5/2020, stripe gives an expiration date
        # on the test token of 3/2021. This may need to be updated
        # in the future.
        now = datetime.now()
        assert customer.card_info() == {
            "brand": "Visa",
            "last4": "0077",
            "exp_month": now.month,
            "exp_year": now.year + 1,
        }

    @pytest.mark.parametrize(
        "plan_duration,other_duration", [("Monthly", "Yearly"), ("Yearly", "Monthly")]
    )
    def test_customer_subscription_upgrades(
        self, db, customer, monkeypatch, plan_duration, other_duration
    ):
        assert customer.current_plan() == {"plan_duration": None, "name": "free"}
        assert customer.current_plan(as_dict=False).plan == Plan.objects.get(
            nickname="Free Plan"
        )

        cs_product = Product.objects.get(name="Compute Studio Subscription")

        # test upgrade from free to pro
        plan = cs_product.plans.get(nickname=f"{plan_duration} Pro Plan")

        result = customer.update_plan(plan)
        assert result == UpdateStatus.upgrade

        customer = Customer.objects.get(pk=customer.pk)
        assert customer.current_plan() == {
            "plan_duration": plan_duration.lower(),
            "name": "pro",
        }

        # test update_plan is idempotent
        plan = cs_product.plans.get(nickname=f"{plan_duration} Pro Plan")

        result = customer.update_plan(plan)
        assert result == UpdateStatus.nochange

        assert customer.current_plan() == {
            "plan_duration": plan_duration.lower(),
            "name": "pro",
        }

        # test downgrade from pro to plus
        plan = cs_product.plans.get(nickname=f"{plan_duration} Plus Plan")

        result = customer.update_plan(plan)
        assert result == UpdateStatus.downgrade

        assert customer.current_plan() == {
            "plan_duration": plan_duration.lower(),
            "name": "plus",
        }

        # swap to other plus duration
        plan = cs_product.plans.get(nickname=f"{other_duration} Plus Plan")

        result = customer.update_plan(plan)
        assert result == UpdateStatus.duration_change

        assert customer.current_plan() == {
            "plan_duration": other_duration.lower(),
            "name": "plus",
        }

        # test upgrade back to pro
        plan = cs_product.plans.get(nickname=f"{plan_duration} Pro Plan")

        result = customer.update_plan(plan)
        assert result == UpdateStatus.upgrade

        assert customer.current_plan() == {
            "plan_duration": plan_duration.lower(),
            "name": "pro",
        }

        # swap to other pro duration
        plan = cs_product.plans.get(nickname=f"{other_duration} Pro Plan")

        result = customer.update_plan(plan)
        assert result == UpdateStatus.duration_change

        assert customer.current_plan() == {
            "plan_duration": other_duration.lower(),
            "name": "pro",
        }

        # test downgrade to free
        plan = Plan.objects.get(nickname="Free Plan")
        result = customer.update_plan(plan)
        assert result == UpdateStatus.downgrade
        assert customer.current_plan() == {"plan_duration": None, "name": "free"}
        assert customer.current_plan(as_dict=False).plan == Plan.objects.get(
            nickname="Free Plan"
        )
