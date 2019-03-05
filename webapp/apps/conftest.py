import os
import json
import datetime

import pytest
import stripe

from django import forms
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.utils.timezone import make_aware

from webapp.apps.billing.models import Customer, Plan, Subscription, SubscriptionItem
from webapp.apps.billing.utils import USE_STRIPE, get_billing_data
from webapp.apps.users.models import Profile, Project

from webapp.apps.core.meta_parameters import MetaParameter, MetaParameters
from webapp.apps.projects.tests.testapp.models import TestappRun, TestappInputs
from webapp.apps.projects.tests.sponsoredtestapp.models import (
    SponsoredtestappRun,
    SponsoredtestappInputs,
)


stripe.api_key = os.environ.get("STRIPE_SECRET")

###########################User/Billing Fixtures###############################
from django.conf import settings


@pytest.fixture(scope="session")
def billing_data():
    return get_billing_data(include_mock_data=True)


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker, billing_data):
    mock_models = ["Used for testing", "Used for testing sponsored apps"]
    with django_db_blocker.unblock():
        User = get_user_model()
        modeler = User.objects.create_user(
            username="modeler", email="modeler@email.com", password="modeler2222"
        )
        Profile.objects.create(user=modeler, is_active=True)
        call_command("init_projects", use_stripe=USE_STRIPE, include_mock_data=True)
        for name, proj in billing_data.items():
            if proj["name"] in mock_models:
                project = Project.objects.get(name=proj["name"])
                project.status = "pending"
                project.save()
            if proj["sponsor"] is None:
                continue
            else:
                username = proj["sponsor"]
                user = User.objects.create_user(
                    username=username, email="sponsor@email.com", password="sponsor2222"
                )
                if USE_STRIPE:
                    stripe_customer = stripe.Customer.create(
                        email="tester@example.com", source="tok_bypassPending"
                    )
                    customer, _ = Customer.get_or_construct(stripe_customer.id, user)
                    customer.subscribe_to_public_plans()
                    customer_user = customer.user
                else:
                    customer_user = user
                Profile.objects.create(user=customer_user, is_active=True)
        call_command("init_projects", use_stripe=USE_STRIPE, include_mock_data=True)


@pytest.fixture
def stripe_customer():
    """
    Default stripe.Customer object where token is valid and
    charge goes through
    """
    customer = stripe.Customer.create(
        email="tester@example.com", source="tok_bypassPending"
    )
    return customer


@pytest.fixture
def password():
    return "heyhey2222"


@pytest.fixture
def user(db, password):
    User = get_user_model()
    user = User.objects.create_user(
        username="tester", email="tester@email.com", password=password
    )
    assert user.username
    assert user.email
    assert user.password
    return user


@pytest.fixture
def basiccustomer(db, stripe_customer, user):
    customer, _ = Customer.get_or_construct(stripe_customer.id, user)
    return customer


@pytest.fixture
def customer(db, basiccustomer):
    basiccustomer.subscribe_to_public_plans()
    assert basiccustomer.subscriptions.count() > 0
    return basiccustomer


@pytest.fixture
def profilewcustomer(db, customer):
    return Profile.objects.create(user=customer.user, is_active=True)


@pytest.fixture
def profile(db, user):
    return Profile.objects.create(user=user, is_active=True)


@pytest.fixture
def plans(db):
    plans = Plan.objects.filter(product__name="Used for testing")
    return plans


@pytest.fixture
def licensed_plan(db, plans):
    assert len(plans) > 0
    return plans.get(usage_type="licensed")


@pytest.fixture
def metered_plan(db, plans):
    assert len(plans) > 0
    return plans.get(usage_type="metered")


@pytest.fixture
def subscription(db, customer, licensed_plan, metered_plan):
    stripe_subscription = Subscription.create_stripe_object(
        customer, [licensed_plan, metered_plan]
    )
    assert stripe_subscription

    subscription, _ = Subscription.get_or_construct(
        stripe_subscription.id, customer=customer, plans=[licensed_plan, metered_plan]
    )

    for raw_si in stripe_subscription["items"]["data"]:
        stripe_si = SubscriptionItem.get_stripe_object(raw_si["id"])
        plan, created = Plan.get_or_construct(raw_si["plan"]["id"])
        assert not created
        si, created = SubscriptionItem.get_or_construct(
            stripe_si.id, plan, subscription
        )
        assert si

    return subscription


@pytest.fixture
def test_models(db, profile):
    project = Project.objects.get(name="Used for testing")
    inputs = TestappInputs.objects.create()
    obj0 = TestappRun.objects.create(
        profile=profile,
        sponsor=project.sponsor,
        project=project,
        run_time=10,
        run_cost=1,
        inputs=inputs,
        creation_date=make_aware(datetime.datetime(2019, 2, 1)),
    )
    assert obj0

    project = Project.objects.get(name="Used for testing sponsored apps")
    inputs = SponsoredtestappInputs.objects.create()
    obj1 = SponsoredtestappRun.objects.create(
        profile=profile,
        sponsor=project.sponsor,
        project=project,
        run_time=10,
        run_cost=1,
        inputs=inputs,
        creation_date=make_aware(datetime.datetime(2019, 1, 1)),
    )
    assert obj1
    return obj0, obj1


############################Core Fixtures###############################
@pytest.fixture
def core_inputs():
    path = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(path, "core/tests/inputs.json")) as f:
        return json.loads(f.read())


@pytest.fixture
def meta_param():
    return MetaParameters(
        parameters=[
            MetaParameter(name="metaparam", default=1, field=forms.IntegerField())
        ]
    )


@pytest.fixture
def valid_meta_params(meta_param):
    return meta_param.validate({})
