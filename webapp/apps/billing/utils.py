import os
from datetime import datetime
import pytz

from webapp.apps.billing.models import Product, Customer

import stripe

# stripe.api_key = os.environ.get("STRIPE_SECRET")


def update_payment(user, stripe_token):
    if hasattr(user, "customer"):
        user.customer.update_source(stripe_token)
    else:  # create customer.
        stripe_customer = stripe.Customer.create(email=user.email, source=stripe_token)
        Customer.construct(stripe_customer, user=user)


def has_payment_method(user):
    return (
        hasattr(user, "customer")
        and user.customer is not None
        and user.customer.card_info() is not None
    )


def create_three_month_pro_subscription(user):
    """
    Gives user a free three month pro subscription that cancels
    at the end of the trial period, unless the user opts into
    the sub after the period ends.
    """
    if getattr(user, "customer", None) is None:
        stripe_customer = stripe.Customer.create(email=user.email)
        customer = Customer.construct(stripe_customer, user=user)
    else:
        customer: Customer = user.customer

    cs_product = Product.objects.get(name="Compute Studio Subscription")
    plan = cs_product.plans.get(nickname=f"Monthly Pro Plan")
    now = datetime.utcnow().replace(tzinfo=pytz.UTC)
    if now.month <= 9:
        three_months = now.replace(month=now.month + 3)
    else:
        three_months = now.replace(year=now.year + 1, month=now.month + 3 - 12)
    customer.update_plan(
        plan, cancel_at=three_months, trial_end=three_months,
    )
