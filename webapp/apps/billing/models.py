import os
from datetime import datetime, timedelta
from datetime import date
import math
from enum import Enum
from typing import Optional

import stripe

import pytz
from django.db import models, IntegrityError
from django.db.models import Q
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.utils import timezone

from webapp.settings import USE_STRIPE, DEBUG

from .email import send_subscribe_to_plan_email, send_sub_canceled_email

stripe.api_key = os.environ.get("STRIPE_SECRET")


def timestamp_to_datetime(timestamp):
    if timestamp is None:
        return None
    if isinstance(timestamp, int):
        timestamp = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
    return timezone.make_aware(datetime.combine(timestamp, datetime.utcnow().time()))


class RequiredLocalInstances(Exception):
    pass


class CustomerManager(models.Manager):
    pass


class UpdateStatus(Enum):
    upgrade = "upgrade"
    downgrade = "downgrade"
    duration_change = "duration_change"
    nochange = "nochange"


# Create your models here.
class Customer(models.Model):
    plan_in_nostripe_mode = "free"
    USD = "usd"
    CURRENCY_CHOICES = ((USD, "usd"),)

    stripe_id = models.CharField(max_length=255, unique=True)
    livemode = models.BooleanField(default=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE
    )
    account_balance = models.DecimalField(
        decimal_places=2, max_digits=9, null=True, blank=True
    )
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default=USD)
    delinquent = models.BooleanField(default=False)
    default_source = models.TextField(blank=True, null=True)
    metadata = JSONField()

    objects = CustomerManager()

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

    def card_info(self):
        """Returns last 4 digits and brand of default source or None"""
        stripe_obj = Customer.get_stripe_object(self.stripe_id)
        default_source = stripe_obj.default_source
        info = (None, None, None, None)
        for source in stripe_obj.sources:
            if source.id == default_source:
                info = (source.brand, source.last4, source.exp_month, source.exp_year)
                break
        if all(info):
            return {
                "brand": info[0],
                "last4": info[1],
                "exp_month": info[2],
                "exp_year": info[3],
            }
        return None

    def invoices(self):
        res = stripe.Invoice.list(customer=self.stripe_id)
        for invoice in res.data:
            yield invoice

    def current_plan(self, si=None, as_dict=True):
        """
        Returns customer's compute studio plan and billing cycle duration
        """
        if not USE_STRIPE:
            if not DEBUG:
                import warnings

                warnings.warn("Stripe mode is not on and you are in production!")
            return {"name": Customer.plan_in_nostripe_mode, "plan_duration": "monthly"}

        product = Product.objects.get(name="Compute Studio Subscription")
        current_plan = {"plan_duration": None, "name": "free"}
        try:
            si = si or SubscriptionItem.objects.get(
                subscription__customer=self, plan__in=product.plans.all()
            )
            if si.plan.nickname == "Free Plan":
                current_plan = {"plan_duration": None, "name": "free"}
            elif si.plan.nickname == "Monthly Pro Plan":
                current_plan = {"plan_duration": "monthly", "name": "pro"}
            elif si.plan.nickname == "Yearly Pro Plan":
                current_plan = {"plan_duration": "yearly", "name": "pro"}

            trial_end_date = None
            cancel_at = None
            sub = si.subscription
            if sub.trial_end is not None:
                trial_end_date = sub.trial_end.date()
            if sub.cancel_at is not None:
                cancel_at = sub.cancel_at.date()
            current_plan["trial_end"] = trial_end_date
            current_plan["cancel_at"] = cancel_at

        except SubscriptionItem.DoesNotExist:
            pass

        if as_dict:
            return current_plan
        else:
            return si

    def update_plan(self, new_plan: Optional["Plan"], **subscription_kwargs):
        current_si = self.current_plan(as_dict=False)
        current_plan = self.current_plan(si=current_si, as_dict=True)

        product = Product.objects.get(name="Compute Studio Subscription")

        # Check change from one paid plan to another.
        if (
            new_plan is not None
            and current_si is not None
            and current_si.plan != new_plan
        ):
            if current_si.plan.nickname == "Free Plan":
                status = UpdateStatus.upgrade

            elif current_si.plan.nickname.endswith("Pro Plan"):

                if new_plan.nickname.endswith("Pro Plan"):
                    status = UpdateStatus.duration_change
                elif new_plan.nickname == "Free Plan":
                    status = UpdateStatus.downgrade

            else:
                raise ValueError(
                    "Can only handle free, and pro plans at the moment: {new_plan.nickname}."
                )

            # Only upgrade takes effect immediately in db.
            # Downgrades will be handled via a webhook.
            if status == UpdateStatus.downgrade:
                stripe_sub: stripe.Subscription = stripe.Subscription.modify(
                    current_si.subscription.stripe_id, cancel_at_period_end=True,
                )
                sub = current_si.subscription
                # Don't trigger downgrade notification if plan already set to
                # end at the end of the billing period.
                if sub.cancel_at_period_end:
                    return UpdateStatus.nochange
                sub.update_from_stripe_obj(stripe_sub)
                sub.save()
                # send_sub_canceled_email(self.user, sub.current_period_end)
            else:
                stripe.SubscriptionItem.modify(
                    current_si.stripe_id, plan=new_plan.stripe_id
                )
                current_si.plan = new_plan
                current_si.save()
                if subscription_kwargs:
                    stripe_sub = stripe.Subscription.modify(
                        current_si.subscription.stripe_id, **subscription_kwargs
                    )
                else:
                    stripe_sub = stripe.Subscription.retrieve(
                        current_si.subscription.stripe_id,
                    )
                current_si.subscription.update_from_stripe_obj(stripe_sub)
                send_subscribe_to_plan_email(self.user, new_plan)
            return status

        # Check nochange transitions
        if current_plan["name"] == "free" and new_plan is None:
            return UpdateStatus.nochange
        if current_si is not None and current_si.plan == new_plan:
            return UpdateStatus.nochange

        # Transition from free to paid plan.
        stripe_sub = Subscription.create_stripe_object(
            self, [new_plan], **subscription_kwargs
        )
        sub = Subscription.construct(
            stripe_sub, self, [new_plan], subscription_type="compute-studio"
        )
        for si_object in stripe_sub["items"]["data"]:
            stripe_si = SubscriptionItem.get_stripe_object(si_object["id"])
            plan = product.plans.get(stripe_id=si_object["plan"]["id"])
            SubscriptionItem.get_or_construct(stripe_si.id, plan, sub)

        return UpdateStatus.upgrade

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
            currency=stripe_customer.currency or "usd",
            delinquent=stripe_customer.delinquent,
            default_source=stripe_customer.default_source,
            metadata=stripe_customer.to_dict(),
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
            customer.update_plan(new_plan=Plan.objects.get(nickname="Free Plan"))
        except IntegrityError:
            customer, created = Customer.objects.get(stripe_id=stripe_id), False
        return customer, created


class Product(models.Model):
    objects: models.Manager
    stripe_id = models.CharField(max_length=255, unique=True)
    project = models.OneToOneField("users.Project", null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    metadata = JSONField()

    @staticmethod
    def create_stripe_object(name):
        product = stripe.Product.create(name=name, type="service")
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
            metadata=stripe_product.to_dict(),
        )
        return product

    @staticmethod
    def get_or_construct(stripe_id, project=None):
        try:
            product, created = Product.objects.get(stripe_id=stripe_id), False
        except Product.DoesNotExist:
            stripe_obj = Product.get_stripe_object(stripe_id)
            product, created = Product.construct(stripe_obj, project), True
        except IntegrityError:
            product, created = Product.objects.get(stripe_id), False
        return (product, created)


class Plan(models.Model):
    objects: models.Manager
    LICENSED = "licensed"
    METERED = "metered"
    USAGE_TYPE_CHOICES = ((LICENSED, "licensed"), (METERED, "metered"))

    SUM = "sum"
    LAST_DURING_PERIOD = "last_during_period"
    MAX = "max"
    LAST_EVER = "last_ever"
    AGG_USAGE_CHOICES = (
        (SUM, "sum"),
        (LAST_DURING_PERIOD, "last_during_period"),
        (MAX, "max"),
        (LAST_EVER, "LAST_EVER"),
    )

    USD = "usd"
    CURRENCY_CHOICES = ((USD, "usd"),)

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    INTERVAL_CHOICES = ((DAY, "day"), (WEEK, "week"), (MONTH, "month"), (YEAR, "year"))
    stripe_id = models.CharField(max_length=255, unique=True)
    active = models.BooleanField(default=False)
    aggregate_usage = models.CharField(
        max_length=18, choices=AGG_USAGE_CHOICES, default=SUM, null=True
    )
    amount = models.IntegerField()
    created = models.DateTimeField(null=True, blank=True)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default=USD)
    interval = models.CharField(max_length=5, choices=INTERVAL_CHOICES, default=MONTH)
    livemode = models.BooleanField(default=False)
    metadata = JSONField()
    nickname = models.CharField(max_length=255)
    product = models.ForeignKey(
        Product, null=True, on_delete=models.CASCADE, related_name="plans"
    )
    trial_period_days = models.IntegerField(default=0, null=True)
    usage_type = models.CharField(max_length=8, choices=USAGE_TYPE_CHOICES)

    @staticmethod
    def create_stripe_object(
        amount, product, usage_type, interval="month", currency="usd", nickname=None
    ):
        nickname = nickname or f"{product.name} {usage_type.title()} {currency}"
        plan = stripe.Plan.create(
            amount=amount,
            nickname=nickname,
            product=product.stripe_id,
            usage_type=usage_type,
            interval=interval,
            currency=currency,
        )
        return plan

    @staticmethod
    def get_stripe_object(stripe_id):
        return stripe.Plan.retrieve(stripe_id)

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
            usage_type=stripe_plan.usage_type,
        )
        return plan

    @staticmethod
    def get_or_construct(stripe_id, product=None):
        try:
            plan, created = Plan.objects.get(stripe_id=stripe_id), False
        except Plan.DoesNotExist:
            if product is None:
                raise RequiredLocalInstances(
                    "Local instance of Product was not provided."
                )
            stripe_plan = Plan.get_stripe_object(stripe_id)
            plan, created = Plan.construct(stripe_plan, product), True
        except IntegrityError:
            plan, created = Plan.objects.get(stripe_id), False
        return (plan, created)


class Subscription(models.Model):
    # raises error on deletion
    subscription_type = models.CharField(
        default="primary",
        choices=[
            ("primary", "Primary"),
            ("compute-studio", "Compute Studio Subscription"),
        ],
        max_length=50,
    )
    stripe_id = models.CharField(max_length=255, unique=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="subscriptions"
    )
    plans = models.ManyToManyField(Plan, related_name="subscriptions")
    livemode = models.BooleanField(default=False)
    metadata = JSONField()
    cancel_at_period_end = models.BooleanField(default=False, null=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    trial_end = models.DateTimeField(null=True, blank=True)

    def update_from_stripe_obj(self, stripe_obj: stripe.Subscription):
        self.current_period_start = timestamp_to_datetime(
            stripe_obj.current_period_start
        )
        self.current_period_end = timestamp_to_datetime(stripe_obj.current_period_end)
        self.cancel_at_period_end = stripe_obj.cancel_at_period_end
        self.canceled_at = timestamp_to_datetime(stripe_obj.canceled_at)
        self.ended_at = timestamp_to_datetime(stripe_obj.ended_at)
        self.cancel_at = timestamp_to_datetime(stripe_obj.cancel_at)
        self.trial_end = timestamp_to_datetime(stripe_obj.trial_end)
        self.save()

    @staticmethod
    def create_stripe_object(
        customer,
        plans,
        coupon: str = None,
        cancel_at: datetime = None,
        trial_end: datetime = None,
    ):
        if trial_end is not None:
            print(trial_end, trial_end.timestamp())
        subscription = stripe.Subscription.create(
            customer=customer.stripe_id,
            items=[{"plan": plan.stripe_id} for plan in plans],
            coupon=coupon,
            cancel_at=int(cancel_at.timestamp()) if cancel_at is not None else None,
            trial_end=int(trial_end.timestamp()) if trial_end is not None else None,
        )
        return subscription

    @staticmethod
    def get_stripe_object(stripe_id):
        return stripe.Subscription.retrieve(stripe_id)

    @staticmethod
    def construct(stripe_subscription, customer, plans, subscription_type="primary"):
        sub = Subscription.objects.create(
            stripe_id=stripe_subscription.id,
            customer=customer,
            livemode=stripe_subscription.livemode,
            metadata=stripe_subscription.to_dict(),
            current_period_start=timestamp_to_datetime(
                stripe_subscription.current_period_start
            ),
            current_period_end=timestamp_to_datetime(
                stripe_subscription.current_period_end
            ),
            cancel_at_period_end=stripe_subscription.cancel_at_period_end,
            subscription_type=subscription_type,
            trial_end=timestamp_to_datetime(stripe_subscription.trial_end),
            cancel_at=timestamp_to_datetime(stripe_subscription.cancel_at),
            canceled_at=timestamp_to_datetime(stripe_subscription.canceled_at),
            ended_at=timestamp_to_datetime(stripe_subscription.ended_at),
        )
        sub.plans.add(*plans)
        sub.save()
        return sub

    @staticmethod
    def get_or_construct(stripe_id, customer=None, plans=None):
        try:
            subscription, created = Subscription.objects.get(stripe_id=stripe_id), False
        except Subscription.DoesNotExist:
            if not customer or not plans:
                raise RequiredLocalInstances(
                    "Local instances of Customer and Plan were not provided."
                )
            stripe_obj = Subscription.get_stripe_object(stripe_id)
            subscription, created = (
                Subscription.construct(stripe_obj, customer, plans),
                True,
            )
        except IntegrityError:
            subscription, created = Subscription.objects.get(stripe_id=stripe_id), False
        return (subscription, created)

    def extend_subscription(self, days=30):
        """
        Extend subscription a month from its end date or now
        if "now" is after the subscription ended.
        """
        base = max(timezone.make_aware(datetime.now()), self.current_period_end)

        self.current_period_end = base + timedelta(days=days)

    def cancel_subscription(self):
        self.canceled_at = timezone.now()
        # allowed to use site until current period is over
        self.ended_at = self.current_period_end

    def is_trial(self):
        if self.trial_end is None:
            return False
        else:
            return timezone.now() < self.trial_end


class SubscriptionItem(models.Model):
    stripe_id = models.CharField(max_length=255, unique=True)
    livemode = models.BooleanField(default=False)
    created = models.DateTimeField()
    plan = models.ForeignKey(
        Plan, on_delete=models.CASCADE, related_name="subscription_items", null=True
    )
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="subscription_items"
    )

    @staticmethod
    def get_stripe_object(stripe_id):
        return stripe.SubscriptionItem.retrieve(stripe_id)

    @staticmethod
    def construct(stripe_subscription_item, plan, subscription):
        created = timestamp_to_datetime(stripe_subscription_item.created)
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
                    "Local instances of Plan and Subscription were not provided."
                )
            stripe_si = SubscriptionItem.get_stripe_object(stripe_id)
            si, created = (
                SubscriptionItem.construct(stripe_si, plan, subscription),
                True,
            )
        except IntegrityError:
            si, created = SubscriptionItem.objects.get(stripe_id), False
        return (si, created)


class Event(models.Model):
    stripe_id = models.CharField(max_length=255, unique=True)
    created = models.DateTimeField()
    data = JSONField()
    livemode = models.BooleanField(default=False)
    # pending_webhooks = models.IntegerField()
    request = models.CharField(max_length=255)
    kind = models.CharField(max_length=64)  # maps to stripe:type
    customer = models.ForeignKey(
        Customer, null=True, on_delete=models.CASCADE, related_name="customer"
    )
    metadata = JSONField()

    @staticmethod
    def construct(stripe_event, customer=None, invoice=None):
        event = Event.objects.create(
            stripe_id=stripe_event.id,
            created=timestamp_to_datetime(stripe_event.created),
            customer=customer,
            data=stripe_event["data"],
            livemode=stripe_event.livemode,
            kind=stripe_event.type,
            metadata=stripe_event.to_dict(),
        )
        return event


def create_pro_billing_objects():
    if Product.objects.filter(name="Compute Studio Subscription").count() == 0:
        stripe_obj = Product.create_stripe_object("Compute Studio Subscription")
        product, _ = Product.get_or_construct(stripe_obj.id)
    else:
        product = Product.objects.get(name="Compute Studio Subscription")

    if product.plans.filter(nickname="Free Plan").count() == 0:
        plan = Plan.create_stripe_object(
            amount=0,
            product=product,
            usage_type="licensed",
            interval="year",
            nickname="Free Plan",
        )
        Plan.get_or_construct(plan.id, product)

    if product.plans.filter(nickname="Monthly Pro Plan").count() == 0:
        monthly_plan = Plan.create_stripe_object(
            amount=int(9 * 100),
            product=product,
            usage_type="licensed",
            interval="month",
            nickname="Monthly Pro Plan",
        )
        Plan.get_or_construct(monthly_plan.id, product)

    if product.plans.filter(nickname="Yearly Pro Plan").count() == 0:
        yearly_plan = Plan.create_stripe_object(
            amount=int(99 * 100),
            product=product,
            usage_type="licensed",
            interval="year",
            nickname="Yearly Pro Plan",
        )
        Plan.get_or_construct(yearly_plan.id, product)
