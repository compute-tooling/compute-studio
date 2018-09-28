import os

import pytest
import stripe

from django.contrib.auth import get_user_model

from webapp.apps.billing.models import (construct,
                                        Customer, Plan, Subscription,
                                        SubscriptionItem)
from webapp.apps.users.models import Profile


stripe.api_key = os.environ.get('STRIPE_SECRET')


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        construct()


@pytest.fixture
def stripe_customer():
    """
    Default stripe.Customer object where token is valid and
    charge goes through
    """
    customer = stripe.Customer.create(email='tester@example.com',
                                      source='tok_bypassPending')
    return customer


@pytest.fixture
def password():
    return 'heyhey2222'


@pytest.fixture
def user(db, password):
    User = get_user_model()
    user = User.objects.create_user(username='tester', email='tester@email.com',
                                    password=password)
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
def profile(db, customer):
    return Profile.create_from_user(customer.user, True)


@pytest.fixture
def plans(db):
    construct()
    plans = Plan.objects.filter(product__name='Descriptive Statistics')
    return plans


@pytest.fixture
def licensed_plan(db, plans):
    assert len(plans) > 0
    for plan in plans:
        if plan.usage_type == 'licensed':
            return plan
    raise ValueError('No plan with usage type: licensed')


@pytest.fixture
def metered_plan(db, plans):
    assert len(plans) > 0
    for plan in plans:
        if plan.usage_type == 'metered':
            return plan
    raise ValueError('No plan with usage type: metered')


@pytest.fixture
def subscription(db, customer, licensed_plan, metered_plan):
    stripe_subscription = Subscription.create_stripe_object(
        customer,
        [licensed_plan, metered_plan])
    assert stripe_subscription

    subscription, _ = Subscription.get_or_construct(
        stripe_subscription.id,
        customer=customer,
        plans=[licensed_plan, metered_plan])

    for raw_si in stripe_subscription['items']['data']:
        stripe_si = SubscriptionItem.get_stripe_object(raw_si['id'])
        plan, created = Plan.get_or_construct(raw_si['plan']['id'])
        assert not created
        si, created = SubscriptionItem.get_or_construct(stripe_si.id, plan,
                                                        subscription)
        assert si

    return subscription
