import os
import time

import stripe

from django.core.mail import send_mail

from .models import Event, Customer
from .events import get_customer_from_event


stripe.api_key = os.environ.get("STRIPE_SECRET")


def invoice_payment_failed(event, link="test"):
    print("processing invoice.payment_failed event...")
    send_mail(
        "Compute Studio",
        "Payment failed",
        "Compute Studio <hank@compute.studio>",
        ["hank@compute.studio"],
        fail_silently=False,
    )


def customer_created(event):
    print("processing customer.created event...")
    customer = Customer.objects.get(stripe_id=event.data["object"]["id"])
    send_mail(
        "Compute Studio",
        "Your payment method was set successfully! Please write back if you have any questions.",
        "Compute Studio <hank@compute.studio>",
        [customer.user.email],
        fail_silently=False,
    )


webhook_map = {
    "invoice.payment_failed": invoice_payment_failed,
    "customer.created": customer_created,
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
