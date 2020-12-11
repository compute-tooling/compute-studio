import math
import os
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model

import pytest
import pytz
import stripe

from webapp.apps.users.models import Profile, Project, create_profile_from_user
from webapp.apps.publish.tests.utils import mock_sync_projects
from webapp.apps.billing.models import (
    Coupon,
    Customer,
    Plan,
    Product,
    Subscription,
    SubscriptionItem,
    create_pro_billing_objects,
    UpdateStatus,
)
from webapp.apps.billing.utils import create_three_month_pro_subscription

User = get_user_model()
stripe.api_key = os.environ.get("STRIPE_SECRET")


def time_is_close(a, b):
    return (a - b).total_seconds() < 3600


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

    @pytest.mark.parametrize("has_pmt_info", [True, False])
    def test_subscription_with_trial_and_coupon(self, db, has_pmt_info, customer):
        """
        Create a subscription with a coupon and trial that expire in 3 months:
        1. User has payment info.
        2. User has no payment info.
        """
        if not has_pmt_info:
            user = User.objects.create_user(
                f"test-coupon", f"test-coupon@example.com", "heyhey2222"
            )
            create_profile_from_user(user)
        else:
            user = customer.user

        create_three_month_pro_subscription(user)

        now = datetime.utcnow().replace(tzinfo=pytz.UTC)
        if now.month < 9:
            three_months = now.replace(month=now.month + 3)
        else:
            three_months = now.replace(year=now.year + 1, month=now.month + 3 - 12)

        user.refresh_from_db()
        customer = getattr(user, "customer", None)
        assert customer is not None

        assert customer.current_plan()["name"] == "pro"

        si = customer.current_plan(as_dict=False)

        assert time_is_close(si.subscription.cancel_at, three_months)
        assert time_is_close(si.subscription.trial_end, three_months)

        sub = stripe.Subscription.retrieve(si.subscription.stripe_id)
        assert abs(sub.cancel_at - int(three_months.timestamp())) < 15
        assert abs(sub.trial_end - int(three_months.timestamp())) < 15

        assert sub.is_trial() is True

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
                Plan.objects.get(nickname="Monthly Pro Plan"),
                Plan.objects.get(nickname="Yearly Pro Plan"),
            ]
        )

        assert set(pro_product.plans.all()) == plans

        assert Coupon.objects.get(name="C/S Pro Coupon")

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

        si = customer.current_plan(as_dict=False)
        assert si.subscription.is_trial() is False
        assert si.subscription.cancel_at is None
        assert si.trial_end is None

        # test update_plan is idempotent
        plan = cs_product.plans.get(nickname=f"{plan_duration} Pro Plan")

        result = customer.update_plan(plan)
        assert result == UpdateStatus.nochange

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
        assert customer.current_plan() == {
            "plan_duration": other_duration.lower(),
            "name": "pro",
        }
        si = customer.current_plan(as_dict=False)
        assert si.plan == Plan.objects.get(nickname=f"{other_duration} Pro Plan")
        assert si.subscription.cancel_at_period_end is True
