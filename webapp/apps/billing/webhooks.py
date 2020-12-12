import os
import time

import stripe

from django.core.mail import send_mail
from django.shortcuts import get_object_or_404

from .models import Event, Customer, Subscription
from .events import get_customer_from_event


stripe.api_key = os.environ.get("STRIPE_SECRET")


def customer_created(event):
    print("processing customer.created event...")
    customer = Customer.objects.get(stripe_id=event.data["object"]["id"])
    send_mail(
        "Payment method updated",
        "Your payment method was set successfully! Please write back if you have any questions.",
        "notifications@compute.studio",
        [customer.user.email],
        fail_silently=False,
    )


def customer_subscription_deleted(event):
    print("processing customer.subscription.deleted event...")
    sub = get_object_or_404(Subscription, stripe_id=event.data.object.id)
    customer = sub.customer
    sub.delete()
    print("successfully deleted subscription")
    send_mail(
        "Your C/S subscription has been cancelled",
        (
            "We are sorry to see you go. If you have a moment, please let us know why "
            "you have cancelled your subscription and what we can do to win you back "
            "in the future.\n\nBest,\nThe C/S Team"
        ),
        "admin@compute.studio",
        [customer.user.email],
        fail_silently=False,
    )


def customer_subscription_updated(event: stripe.Event):
    print("processing customer.subscription.updated event...")
    stripe_sub: stripe.Subscription = event.data.object
    sub: Subscription = get_object_or_404(Subscription, stripe_id=stripe_sub.id)
    sub.update_from_stripe_obj(stripe_sub)


webhook_map = {
    "customer.created": customer_created,
    "customer.subscription.deleted": customer_subscription_deleted,
    "customer.subscription.updated": customer_subscription_updated,
}


def process_event(stripe_event):
    start = time.time()
    print("got event: ")
    print(stripe_event)
    customer = get_customer_from_event(stripe_event)
    event = Event.construct(stripe_event, customer=customer)

    func = webhook_map.get(event.kind, None)
    if func is not None:
        try:
            func(event)
        except Exception as e:
            import traceback

            traceback.print_exc()

    total_time = time.time() - start
    print(f"done {total_time}")
