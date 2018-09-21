import os

import stripe

from .models import Customer


stripe.api_key = os.environ.get('STRIPE_SECRET')


def get_customer_from_event(stripe_event):
    customer_events = ['customer.created', 'customer.updated', 
                    'customer.deleted']
    customer = None
    if stripe_event.type in customer_events:
        stripe_customer_id = stripe_event.data['object']['id']
        customer, flag = Customer.get_or_construct(stripe_id=stripe_customer_id)
        assert not (flag and stripe_event.livemode)
    elif 'customer' in stripe_event.data['object']:
        stripe_customer_id = stripe_event.data['object']['customer']
        customer, flag = Customer.get_or_construct(stripe_id=stripe_customer_id)
        assert not (flag and stripe_event.livemode)
    return customer


def get_invoice_from_event(stripe_event):
    pass
