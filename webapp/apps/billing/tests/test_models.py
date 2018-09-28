import math
from datetime import datetime

from django.contrib.auth import get_user_model

import pytest

from webapp.apps.billing.models import (get_billing_data,
                                        Customer, Plan, Product,
                                        Subscription, SubscriptionItem,
                                        UsageRecord)


User = get_user_model()


@pytest.mark.django_db
class TestStripeModels():

    def test_construct_customer(self, stripe_customer, user):
        stripe_customer = Customer.get_stripe_object(stripe_customer.id)
        assert stripe_customer
        assert not stripe_customer.livemode

        customer, created = Customer.get_or_construct(stripe_customer.id, user)
        assert customer
        assert customer.user
        assert created
        assert not customer.livemode

        customer, created = Customer.get_or_construct(stripe_customer.id)
        assert customer
        assert customer.user
        assert not created
        assert not customer.livemode

    def test_construct(self):
        billing = get_billing_data()
        assert 'upload' in billing
        products = Product.objects.all()
        assert len(products) == len(billing)
        name = billing['upload']['name']
        product = Product.objects.get(name=name)
        assert product.project.name == product.name
        assert Plan.objects.filter(product__name=name).count() == 2

    def test_construct_subscription(self, basiccustomer, licensed_plan,
                                    metered_plan):
        stripe_subscription = Subscription.create_stripe_object(
            basiccustomer,
            [licensed_plan, metered_plan])
        assert stripe_subscription

        subscription, created = Subscription.get_or_construct(
            stripe_subscription.id,
            customer=basiccustomer,
            plans=[licensed_plan, metered_plan])

        for raw_si in stripe_subscription['items']['data']:
            stripe_si = SubscriptionItem.get_stripe_object(raw_si['id'])
            plan, created = Plan.get_or_construct(raw_si['plan']['id'])
            assert not created
            si, created = SubscriptionItem.get_or_construct(stripe_si.id, plan,
                                                            subscription)
            assert created
            assert si
            assert si.stripe_id == raw_si['id']
            assert si.plan == plan
            assert si.subscription == subscription

        assert subscription
        assert created
        assert subscription.customer == basiccustomer
        qs = Subscription.objects.filter(
            plans__stripe_id=licensed_plan.stripe_id,
            customer__stripe_id=basiccustomer.stripe_id)
        assert qs.count() == 1
        assert subscription.subscription_items.count() == 2

        subscription, created = Subscription.get_or_construct(
            stripe_subscription.stripe_id)

        assert subscription
        assert not created
        assert subscription.customer == basiccustomer
        assert subscription.subscription_items.count() == 2


    def test_metered_subscription_item(self, subscription):
        assert subscription
        si = subscription.subscription_items.get(plan__usage_type='metered')
        assert si
        assert si.plan.usage_type == 'metered'
        ts = math.floor(datetime.now().timestamp())
        stripe_usage_record = UsageRecord.create_stripe_object(
            quantity=10,
            timestamp=ts,
            subscription_item=si,
            action='increment')
        assert stripe_usage_record
        print('one', stripe_usage_record)
        usage_record = UsageRecord.construct(
            stripe_usage_record,
            si)

        assert usage_record
        assert usage_record.stripe_id == stripe_usage_record.id
        assert usage_record.livemode == False
        assert usage_record.action == 'increment'
        assert usage_record.quantity == 10
        assert usage_record.subscription_item == si
        # TODO: identify second usage_record problem
        # ts = math.floor(datetime.now().timestamp())
        # stripe_usage_record = UsageRecord.create_stripe_object(
        #     quantity=10,
        #     timestamp=ts,
        #     subscription_item=si,
        #     action='increment')

        # usage_record = UsageRecord.construct(
        #     stripe_usage_record,
        #     si)

        # assert usage_record
        # assert usage_record.stripe_id == stripe_usage_record.id
        # assert usage_record.quantity == 10


    def test_update_customer(self, customer):
        tok = 'tok_bypassPending'
        prev_source = customer.default_source
        customer.update_source(tok)
        assert customer.default_source != prev_source

    def test_cancel_subscriptions(self, customer):
        for sub in customer.subscriptions.all():
            assert not sub.cancel_at_period_end
        customer.cancel_subscriptions()
        for sub in customer.subscriptions.all():
            assert sub.cancel_at_period_end