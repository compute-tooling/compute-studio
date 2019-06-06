import os
import json
import datetime
import functools

import requests
import pytest
import stripe
import paramtools

from django import forms
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.utils.timezone import make_aware
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from webapp.apps.billing.models import (
    Customer,
    Product,
    Plan,
    Subscription,
    SubscriptionItem,
)
from webapp.apps.billing.utils import USE_STRIPE
from webapp.apps.users.models import Profile, Project

from webapp.apps.comp.meta_parameters import translate_to_django
from webapp.apps.comp.models import Inputs, Simulation


stripe.api_key = os.environ.get("STRIPE_SECRET")

###########################User/Billing Fixtures###############################
from django.conf import settings


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        User = get_user_model()
        modeler = User.objects.create_user(
            username="modeler", email="modeler@email.com", password="modeler2222"
        )

        sponsor = User.objects.create_user(
            username="sponsor", email="sponsor@email.com", password="sponsor2222"
        )

        hdoupe = User.objects.create_user(
            username="hdoupe", email="hdoupe@email.com", password="hdoupe2222"
        )

        for u in [modeler, sponsor, hdoupe]:
            Token.objects.create(user=u)
            Profile.objects.create(user=u, is_active=True)

        # User for pushing outputs from the workers to the webapp.
        comp_api_user = User.objects.create_user(
            username="comp-api-user",
            email="comp-api-user@email.com",
            password="heyhey2222",
        )
        Profile.objects.create(user=comp_api_user, is_active=True)

        common = {
            "description": "[Matchups](https://github.com/hdoupe/Matchups) provides pitch data on pitcher and batter matchups.. Select a date range using the format YYYY-MM-DD. Keep in mind that Matchups only provides data on matchups going back to 2008. Two datasets are offered to run this model: one that only has the most recent season, 2018, and one that contains data on every single pitch going back to 2008. Next, select your favorite pitcher and some batters who he's faced in the past. Click submit to start analyzing the selected matchups!",
            "oneliner": "oneliner",
            "repo_url": "https://github.com/hdoupe/Matchups",
            "server_size": ["8,2"],
            "exp_task_time": 10,
            "owner": modeler.profile,
            "server_cost": 0.1,
            "listed": True,
        }

        projects = [
            {"title": "Matchups", "owner": hdoupe.profile},
            {"title": "Used-for-testing", "listed": False},
            {"title": "Tax-Brain"},
            {"title": "Used-for-testing-sponsored-apps", "sponsor": sponsor.profile},
        ]

        for project_config in projects:
            project = Project.objects.create(**dict(common, **project_config))

        if USE_STRIPE:
            Project.objects.sync_products()
            for u in [modeler, sponsor, hdoupe]:
                stripe_customer = stripe.Customer.create(
                    email=u.email, source="tok_bypassPending"
                )
                customer, _ = Customer.get_or_construct(stripe_customer.id, u)
            Customer.objects.sync_subscriptions()


@pytest.fixture
def api_client():
    return APIClient()


def use_stripe(func):
    @functools.wraps(func)
    def f(*args, **kwargs):
        if USE_STRIPE:
            return func(*args, **kwargs)
        else:
            return None

    return f


@pytest.fixture
@use_stripe
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
    Token.objects.create(user=user)
    assert user.username
    assert user.email
    assert user.password
    assert user.auth_token
    return user


@pytest.fixture
@use_stripe
def basiccustomer(db, stripe_customer, user):
    customer, _ = Customer.get_or_construct(stripe_customer.id, user)
    return customer


@pytest.fixture
@use_stripe
def customer(db, basiccustomer):
    basiccustomer.sync_subscriptions()
    assert basiccustomer.subscriptions.count() > 0
    return basiccustomer


@pytest.fixture
def profile(db, user, customer):
    if customer:
        return Profile.objects.create(user=customer.user, is_active=True)
    else:
        return Profile.objects.create(user=user, is_active=True)


@pytest.fixture
def plans(db):
    plans = Plan.objects.filter(product__name="modeler/Used-for-testing")
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
    project = Project.objects.get(title="Used-for-testing")
    inputs = Inputs.objects.create(project=project)
    obj0 = Simulation.objects.create(
        owner=profile,
        project=project,
        run_time=10,
        run_cost=1,
        inputs=inputs,
        creation_date=make_aware(datetime.datetime(2019, 2, 1)),
        model_pk=Simulation.objects.next_model_pk(project),
    )
    assert obj0

    project = Project.objects.get(title="Used-for-testing-sponsored-apps")
    inputs = Inputs.objects.create(project=project)
    obj1 = Simulation.objects.create(
        owner=profile,
        sponsor=project.sponsor,
        project=project,
        run_time=10,
        run_cost=1,
        inputs=inputs,
        creation_date=make_aware(datetime.datetime(2019, 1, 1)),
        model_pk=Simulation.objects.next_model_pk(project),
    )
    assert obj1
    return obj0, obj1


############################Core Fixtures###############################


@pytest.fixture
def comp_inputs_json():
    path = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(path, "comp/tests/inputs.json")) as f:
        return json.loads(f.read())


@pytest.fixture
def meta_param_dict(comp_inputs_json):
    return comp_inputs_json["meta_param_dict"]


@pytest.fixture
def meta_param(meta_param_dict):
    return translate_to_django(meta_param_dict)


@pytest.fixture
def valid_meta_params(meta_param):
    return meta_param.validate({})


@pytest.fixture
def get_inputs(comp_inputs_json):
    schema = {
        "schema": {
            "additional_members": {
                "section_1": {"type": "str"},
                "section_2": {"type": "str"},
            }
        }
    }

    class Params1(paramtools.Parameters):
        defaults = dict(comp_inputs_json["model_params"]["majorsection1"], **schema)

    class Params2(paramtools.Parameters):
        defaults = dict(comp_inputs_json["model_params"]["majorsection2"], **schema)

    class MetaParams(paramtools.Parameters):
        array_first = True
        defaults = comp_inputs_json["meta_param_dict"]

    p1 = Params1().specification(serializable=True, meta_data=True)
    p2 = Params2().specification(serializable=True, meta_data=True)
    mp = MetaParams().specification(serializable=True, meta_data=True)
    return mp, {"majorsection1": p1, "majorsection2": p2}
