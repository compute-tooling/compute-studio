import os
from datetime import datetime, timedelta
from datetime import date
import math

import stripe

from django.db import models, IntegrityError
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.utils.timezone import make_aware

from webapp.apps.users.models import Project

stripe.api_key = os.environ.get('STRIPE_SECRET')


def timestamp_to_datetime(timestamp):
    if timestamp is None:
        return None
    if isinstance(timestamp, int):
        timestamp = date.fromtimestamp(timestamp)
    return make_aware(
        datetime.combine(timestamp, datetime.now().time())
    )


class RequiredLocalInstances(Exception):
    pass


# Create your models here.
class Customer(models.Model):
    USD = 'usd'
    CURRENCY_CHOICES = (
        (USD, 'usd'),
    )

    stripe_id = models.CharField(max_length=255, unique=True)
    livemode = models.BooleanField(default=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                null=True,
                                on_delete=models.CASCADE)
    account_balance = models.DecimalField(decimal_places=2, max_digits=9, null=True,
                                          blank=True)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default=USD)
    delinquent = models.BooleanField(default=False)
    default_source = models.TextField(blank=True, null=True)
    metadata = JSONField()

    def cancel_subscriptions(self):
        subscriptions = self.subscriptions.all()
        for sub in subscriptions:
            stripe_sub = Subscription.get_stripe_object(sub.stripe_id)
            stripe_sub.cancel_at_period_end = True
            updated_sub = stripe_sub.save()
            sub.update_from_stripe_obj(updated_sub)

    def update_source(self, stripe_token):
        stripe_customer = stripe.Customer.retrieve(self.stripe_id)
        stripe_customer.source = stripe_token
        stripe_customer.save()
        self.default_source = stripe_token
        self.save()

    def subscribe_to_public_plans(self):
        public_plans = Plan.get_public_plans(usage_type='metered')
        stripe_sub = Subscription.create_stripe_object(self, public_plans)
        sub = Subscription.construct(stripe_sub, self, public_plans)
        for raw_si in stripe_sub['items']['data']:
            stripe_si = SubscriptionItem.get_stripe_object(raw_si['id'])
            plan = public_plans.get(stripe_id=raw_si['plan']['id'])
            si, created = SubscriptionItem.get_or_construct(stripe_si.id, plan,
                                                            sub)

    @staticmethod
    def get_stripe_object(stripe_id):
        return stripe.Customer.retrieve(stripe_id)

    @staticmethod
    def construct(stripe_customer, user=None):
        customer = Customer.objects.create(
            stripe_id=stripe_customer.id,
            livemode=stripe_customer.livemode,
            user=user,
            account_balance=stripe_customer.account_balance,
            currency=stripe_customer.currency or 'usd',
            delinquent=stripe_customer.delinquent,
            default_source=stripe_customer.default_source,
            metadata=stripe_customer.to_dict()
        )
        return customer

    @staticmethod
    def get_or_construct(stripe_id, user=None):
        """
        Try to get existing customer. If customer does not exist, retrieve
        customer from Stripe and construct local customer

        returns:
        customer: customer instance
        created: indicates whether a new customer was created
        """
        try:
            customer, created = Customer.objects.get(stripe_id=stripe_id), False
        except Customer.DoesNotExist as dne:
            stripe_obj = Customer.get_stripe_object(stripe_id)
            customer, created = Customer.construct(stripe_obj, user), True
        except IntegrityError:
            customer, created = Customer.objects.get(stripe_id=stripe_id), False
        return customer, created


class Charge(models.Model):
    SUCCEEDED = 'succeeded'
    PENDING = 'pending'
    FAIL = 'failed'
    STATUS_CHOICES = (
        ('succeeded', 'succeeded'),
        ('pending', 'pending'),
        ('failed', 'failed'),
    )

    USD = 'usd'
    CURRENCY_CHOICES = (
        (USD, 'usd'),
    )

    stripe_id = models.CharField(max_length=255, unique=True)
    amount = models.IntegerField()
    amount_refunded = models.IntegerField()
    balance_transaction = models.CharField(max_length=255)
    captured = models.BooleanField(default=False)
    created = models.DateTimeField()
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default=USD)
    customer = models.ForeignKey("Customer", on_delete=models.CASCADE,
                                 related_name="charges")
    dispute = models.BooleanField(default=False)
    livemode = models.BooleanField(default=False)
    paid = models.BooleanField(null=True, blank=True)
    receipt_email = models.CharField(max_length=800, default='', blank=True)
    refunded = models.BooleanField(default=False)
    status = models.CharField(max_length=9, choices=STATUS_CHOICES,
                              default=PENDING)

    @staticmethod
    def get_stripe_object(stripe_id):
        return stripe.Charge.retrieve(stripe_id)

    @staticmethod
    def constuct(stripe_charge, customer):
        charge = Charge.objects.create(
            stripe_id=stripe_charge.id,
            amount=stripe_charge.amount,
            amount_refunded=stripe_charge.amount_refunded,
            balance_transaction=stripe_charge.balance_transaction,
            captured=stripe_charge.balance,
            created=stripe_charge.created,
            currency=stripe_charge.currency,
            customer=customer,
            dispute=stripe_charge.dispute,
            paid=stripe_charge.paid,
            receipt_email=stripe_charge.receipt_email,
            refunded=stripe_charge.refunded,
            status=stripe_charge.status)
        return charge


class Invoice(models.Model):
    USD = 'usd'
    CURRENCY_CHOICES = (
        (USD, 'usd'),
    )

    # see https://stripe.com/docs/api#invoice_object
    stripe_id = models.CharField(max_length=255, unique=True)
    attempt_count = models.IntegerField()
    attempted = models.BooleanField(default=False)
    charge = models.OneToOneField("Charge", on_delete=models.CASCADE, null=True,
                                  related_name="latest_invoice")
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='usd', )
    customer = models.ForeignKey("Customer", on_delete=models.PROTECT,
                                 related_name="invoices")
    description = models.TextField(blank=True)
    ending_balance = models.IntegerField(null=True)
    forgiven = models.BooleanField(default=False)
    hosted_invoice_url = models.CharField(max_length=799, default="", blank=True)
    invoice_pdf = models.CharField(max_length=799, default="", blank=True)
    livemode = models.BooleanField(default=False)
    paid = models.BooleanField(default=False)
    period_end = models.DateTimeField()
    period_start = models.DateTimeField()
    receipt_number = models.CharField(max_length=64, null=True,)
    starting_balance = models.IntegerField()
    statement_descriptor = models.CharField(max_length=22, default="", blank=True)
    subscription = models.ForeignKey("Subscription", null=True, related_name="invoices",
                                     on_delete=models.SET_NULL)
    subscription_proration_date = models.DateTimeField(null=True, blank=True)
    subtotal = models.IntegerField(null=True, blank=True)
    tax = models.IntegerField(null=True, blank=True)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    total = models.IntegerField()

    @staticmethod
    def construct(stripe_invoice, charge, customer, subscription):
        invoice = Invoice.objects.create(
            stripe_id=stripe_invoice.stripe_id,
            attempt_count=stripe_invoice.attempt_count,
            attempted=stripe_invoice.attempted,
            charge=charge,
            currency=stripe_invoice.currency,
            customer=customer,
            ending_balance=stripe_invoice.ending_balance,
            forgiven=stripe_invoice.forgiven,
            hosted_invoice_url=stripe_invoice.hosted_invoice_url,
            invoice_pdf=stripe_invoice.invoice_pdf,
            livemode=stripe_invoice.livemode,
            paid=stripe_invoice.paid,
            period_end=stripe_invoice.period_end,
            period_start=stripe_invoice.period_start,
            subscription=subscription,
            subtotal=stripe_invoice.subtotal,
            tax=stripe_invoice.tax,
            tax_percent=stripe_invoice.tax_percent,
            total=stripe_invoice.total
        )
        return invoice

    @staticmethod
    def get_or_construct(stripe_id, charge=None, customer=None,
                         subscription=None):
        try:
            invoice, created = Invoice.objects.get(stripe_id=stripe_id), False
        except Invoice.DoesNotExist:
            if (charge is None or customer is None or subscription is None):
                raise RequiredLocalInstances(
                    ('Local instances of Charge, Customer, '
                     'and/or subscription were not provided.'))
            stripe_obj = Invoice.get_stripe_object(stripe_id)
            (invoice,
                created) = Invoice.objects.create(stripe_obj, charge, customer,
                                                      subscription), True
        except IntegrityError:
            invoice, created = Invoice.objects.get(stripe_id)
        return invoice, created


class Product(models.Model):
    stripe_id = models.CharField(max_length=255, unique=True)
    project = models.OneToOneField(Project, null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    metadata = JSONField()

    @staticmethod
    def create_stripe_object(name):
        product = stripe.Product.create(
            name=name,
            type='service',
        )
        return product

    @staticmethod
    def get_stripe_object(stripe_id):
        return stripe.Product.retrieve(stripe_id)

    @staticmethod
    def construct(stripe_product, project):
        product = Product.objects.create(
            stripe_id=stripe_product.id,
            project=project,
            name=stripe_product.name,
            metadata=stripe_product.to_dict()
        )
        return product

    @staticmethod
    def get_or_construct(stripe_id, project=None):
        try:
            product, created = Product.objects.get(stripe_id), False
        except Product.DoesNotExist:
            if product is None:
                raise RequiredLocalInstances(
                    'Local instance of Project was not provided.')
            stripe_obj = Product.get_stripe_object(stripe_id)
            product, created = Product.construct(stripe_obj, project), True
        except IntegrityError:
            product, created = Product.objects.get(stripe_id), False
        return (product, created)


class Plan(models.Model):
    LICENSED = 'licensed'
    METERED = 'metered'
    USAGE_TYPE_CHOICES = (
        (LICENSED, 'licensed'),
        (METERED, 'metered'),
    )

    SUM = 'sum'
    LAST_DURING_PERIOD = 'last_during_period'
    MAX = 'max'
    LAST_EVER = 'last_ever'
    AGG_USAGE_CHOICES = (
        (SUM, 'sum'),
        (LAST_DURING_PERIOD, 'last_during_period'),
        (MAX, 'max'),
        (LAST_EVER, 'LAST_EVER'),
    )

    USD = 'usd'
    CURRENCY_CHOICES = (
        (USD, 'usd'),
    )

    DAY = 'day'
    WEEK = 'week'
    MONTH = 'month'
    YEAR = 'year'
    INTERVAL_CHOICES = (
        (DAY, 'day'),
        (WEEK, 'week'),
        (MONTH, 'month'),
        (YEAR, 'year'),
    )
    stripe_id = models.CharField(max_length=255, unique=True)
    active = models.BooleanField(default=False)
    aggregate_usage = models.CharField(max_length=18, choices=AGG_USAGE_CHOICES,
                                       default=SUM, null=True)
    amount = models.IntegerField()
    created = models.DateTimeField(null=True, blank=True)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default=USD)
    interval = models.CharField(max_length=5, choices=INTERVAL_CHOICES, default=MONTH)
    livemode = models.BooleanField(default=False)
    metadata = JSONField()
    nickname = models.CharField(max_length=255)
    product = models.ForeignKey(Product, null=True, on_delete=models.CASCADE,
                                related_name='plans')
    trial_period_days = models.IntegerField(default=0, null=True)
    usage_type = models.CharField(max_length=8, choices=USAGE_TYPE_CHOICES)

    @staticmethod
    def create_stripe_object(amount, product, usage_type,
                             interval='month', currency='usd'):
        nickname = f'{product.name} {usage_type.title()} {currency}'
        plan = stripe.Plan.create(
            amount=amount,
            nickname=nickname,
            product=product.stripe_id,
            usage_type=usage_type,
            interval=interval,
            currency=currency)
        return plan

    @staticmethod
    def get_stripe_object(stripe_id):
        return stripe.Plan.get(stripe_id)

    @staticmethod
    def construct(stripe_plan, product):
        plan = Plan.objects.create(
            stripe_id=stripe_plan.id,
            active=stripe_plan.active,
            aggregate_usage=stripe_plan.aggregate_usage,
            amount=stripe_plan.amount,
            created=timestamp_to_datetime(stripe_plan.created),
            currency=stripe_plan.currency,
            interval=stripe_plan.interval,
            livemode=stripe_plan.livemode,
            metadata=stripe_plan.to_dict(),
            nickname=stripe_plan.nickname,
            product=product,
            trial_period_days=stripe_plan.trial_period_days,
            usage_type=stripe_plan.usage_type)
        return plan

    @staticmethod
    def get_or_construct(stripe_id, product=None):
        try:
            plan, created = Plan.objects.get(stripe_id=stripe_id), False
        except Plan.DoesNotExist:
            if product is None:
                raise RequiredLocalInstances('Local instance of Product was not provided.')
            stripe_plan = Plan.get_stripe_object(stripe_id)
            plan, created = Plan.construct(stripe_plan, product), True
        except IntegrityError:
            plan, created = Plan.objects.get(stripe_id), False
        return (plan, created)

    @staticmethod
    def get_public_plans(**kwargs):
        return Plan.objects.filter(product__project__is_public=True, **kwargs)

class Subscription(models.Model):
    # raises error on deletion
    stripe_id = models.CharField(max_length=255, unique=True)
    customer = models.ForeignKey(Customer,
                                 on_delete=models.CASCADE,
                                 related_name='subscriptions')
    plans = models.ManyToManyField(Plan,
                                   related_name="subscriptions")
    livemode = models.BooleanField(default=False)
    metadata = JSONField()
    cancel_at_period_end = models.BooleanField(default=False, null=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    def update_from_stripe_obj(self, stripe_obj):
        self.current_period_start = timestamp_to_datetime(
            stripe_obj.current_period_start)
        self.current_period_end = timestamp_to_datetime(
            stripe_obj.current_period_end)
        self.cancel_at_period_end = stripe_obj.cancel_at_period_end
        self.canceled_at = timestamp_to_datetime(
            stripe_obj.canceled_at)
        self.ended_at = timestamp_to_datetime(stripe_obj.ended_at)
        self.save()

    @staticmethod
    def create_stripe_object(customer, plans, usage=0.0):
        subscription = stripe.Subscription.create(
            customer=customer.stripe_id,
            items=[{'plan': plan.stripe_id} for plan in plans]
        )
        return subscription

    @staticmethod
    def get_stripe_object(stripe_id):
        return stripe.Subscription.retrieve(stripe_id)

    @staticmethod
    def construct(stripe_subscription, customer, plans, usage=0.0):
        current_period_start = timestamp_to_datetime(
            stripe_subscription.current_period_start)
        current_period_end = timestamp_to_datetime(
            stripe_subscription.current_period_end)
        sub = Subscription.objects.create(
            stripe_id=stripe_subscription.id,
            customer=customer,
            livemode=stripe_subscription.livemode,
            metadata=stripe_subscription.to_dict(),
            current_period_start=current_period_start,
            current_period_end=current_period_end,
        )
        sub.plans.add(*plans)
        sub.save()
        return sub

    @staticmethod
    def get_or_construct(stripe_id, customer=None, plans=None):
        try:
            subscription, created = Subscription.objects.get(stripe_id=stripe_id), False
        except Subscription.DoesNotExist:
            if (not customer or not plans):
                raise RequiredLocalInstances('Local instances of Customer and Plan were not provided.')
            stripe_obj = Subscription.get_stripe_object(stripe_id)
            subscription, created = Subscription.construct(stripe_obj, customer, plans), True
        except IntegrityError:
            subscription, created = Subscription.objects.get(stripe_id=stripe_id), False
        return (subscription, created)


    def extend_subscription(self, days=30):
        """
        Extend subscription a month from its end date or now
        if "now" is after the subscription ended.
        """
        base = max(make_aware(datetime.now()),
                   self.current_period_end)

        self.current_period_end = base + timedelta(days=days)

    def cancel_subscription(self):
        self.canceled_at = make_aware(datetime.now())
        # allowed to use site until current period is over
        self.ended_at = self.current_period_end


class SubscriptionItem(models.Model):
    stripe_id = models.CharField(max_length=255, unique=True)
    livemode = models.BooleanField(default=False)
    created = models.DateTimeField()
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT,
                             related_name="subscription_items")
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE,
                                     related_name="subscription_items")

    @staticmethod
    def get_stripe_object(stripe_id):
        return stripe.SubscriptionItem.retrieve(stripe_id)

    @staticmethod
    def construct(stripe_subscription_item, plan, subscription):
        created = timestamp_to_datetime(
            stripe_subscription_item.created)
        subscription_item = SubscriptionItem.objects.create(
            stripe_id=stripe_subscription_item.id,
            livemode=subscription.livemode,  # stripe obj doesn't have livemode
            created=created,
            plan=plan,
            subscription=subscription,
        )
        return subscription_item

    @staticmethod
    def get_or_construct(stripe_id, plan=None, subscription=None):
        try:
            si, created = SubscriptionItem.objects.get(stripe_id=stripe_id), False
        except SubscriptionItem.DoesNotExist:
            if plan is None or subscription is None:
                raise RequiredLocalInstances(
                    'Local instances of Plan and Subscription were not provided.'
                )
            stripe_si = SubscriptionItem.get_stripe_object(stripe_id)
            si, created = SubscriptionItem.construct(stripe_si, plan, subscription), True
        except IntegrityError:
            si, created = SubscriptionItem.objects.get(stripe_id), False
        return (si, created)


class UsageRecord(models.Model):
    INC = 'increment'
    SET = 'set'
    ACTION_CHOICES= (
        (INC, 'increment'),
        (SET, 'set'),
    )
    stripe_id = models.CharField(max_length=255, unique=True)
    livemode = models.BooleanField(default=False)
    action = models.CharField(max_length=9, choices=ACTION_CHOICES,
                              default=INC)
    quantity = models.IntegerField(default=0)
    subscription_item = models.ForeignKey(SubscriptionItem,
                                          on_delete=models.CASCADE,
                                          related_name='usage_records')
    timestamp = models.DateTimeField()

    @staticmethod
    def create_stripe_object(quantity, timestamp, subscription_item,
                             action='increment'):
        stripe_usage_record = stripe.UsageRecord.create(
            quantity=quantity,
            # None implies now
            timestamp=timestamp or math.floor(datetime.now().timestamp()),
            subscription_item=subscription_item.stripe_id,
            action=action)
        return stripe_usage_record

    @staticmethod
    def get_stripe_object(stripe_id):
        """
        `stripe.UsageRecord` does not have a `get` method
        """
        raise NotImplementedError()

    @staticmethod
    def construct(stripe_usage_record, subscription_item):
        print('construct', stripe_usage_record)
        usage_record = UsageRecord.objects.create(
            stripe_id=stripe_usage_record.id,
            livemode=stripe_usage_record.livemode,
            quantity=stripe_usage_record.quantity,
            subscription_item=subscription_item,
            timestamp=timestamp_to_datetime(stripe_usage_record.timestamp))
        return usage_record

    @staticmethod
    def get_or_construct(stripe_id, subscription_item=None):
        try:
            (usage_record,
                created) = UsageRecord.objects.get(stripe_id=stripe_id), False
        except IntegrityError:
            usage_record, created = UsageRecord.objects.get(stripe_id), False
        return (usage_record, created)


class Event(models.Model):
    stripe_id = models.CharField(max_length=255, unique=True)
    created = models.DateTimeField()
    data = JSONField()
    livemode = models.BooleanField(default=False)
    # pending_webhooks = models.IntegerField()
    request = models.CharField(max_length=255)
    kind = models.CharField(max_length=64) # maps to stripe:type
    customer = models.ForeignKey(Customer, null=True, on_delete=models.CASCADE,
                                 related_name='customer')
    invoice = models.ForeignKey(Invoice, null=True, on_delete=models.CASCADE,
                                related_name='invoice')
    charge = models.ForeignKey(Charge, null=True, on_delete=models.CASCADE,
                               related_name='charge')
    metadata = JSONField()

    @staticmethod
    def construct(stripe_event, customer=None, invoice=None, charge=None):
        event = Event.objects.create(
            stripe_id=stripe_event.id,
            created=timestamp_to_datetime(stripe_event.created),
            customer=customer,
            data=stripe_event['data'],
            invoice=invoice,
            charge=charge,
            livemode=stripe_event.livemode,
            kind=stripe_event.type,
            metadata=stripe_event.to_dict()
        )
        return event


def get_billing_data():
    import json
    path = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(path, 'billing.json')) as f:
        billing = json.loads(f.read())
    return billing


def construct():
    billing = get_billing_data()
    for app_name, plan in billing.items():
        project, _ = Project.objects.update_or_create(
            name=plan['name'],
            defaults={'server_cost': plan['server_cost'],
                      'exp_task_time': plan['exp_task_time'],
                      'is_public': plan['is_public']})
        if Product.objects.filter(name=plan['name']).count() == 0:
            stripe_product = Product.create_stripe_object(plan['name'])
            product = Product.construct(stripe_product, project)
            stripe_plan_lic = Plan.create_stripe_object(
                amount=plan['amount'],
                product=product,
                usage_type='licensed',
                interval=plan['interval'],
                currency=plan['currency'])
            Plan.construct(stripe_plan_lic, product)
            stripe_plan_met = Plan.create_stripe_object(
                amount=plan['metered_amount'],
                product=product,
                usage_type='metered',
                interval=plan['interval'],
                currency=plan['currency'])
            Plan.construct(stripe_plan_met, product)
