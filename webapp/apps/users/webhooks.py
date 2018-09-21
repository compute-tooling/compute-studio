import os
import time

import stripe

from django.core.mail import send_mail

from .models import Event, Customer
from .events import get_customer_from_event


stripe.api_key = os.environ.get('STRIPE_SECRET')


def invoice_payment_failed(event, link='test'):
    print('processing invoice.payment_failed event...')
    print('sending mail...')
    user = event.customer.user
    if hasattr(user, 'email'):
        target_email = user.email
    else:
        target_email = 'thecompmodels@gmail.com'
    send_mail('Your Payment Failed',
              f'Please pay the invoice at: {link}',
              'thecompmodels@gmail.com',
              [target_email],
              fail_silently=False)


def customer_created(event):
    print('processing customer.created event...')
    customer = Customer.objects.get(stripe_id=event.data['object']['id'])
    send_mail(
        'Welcome to COMP',
        'Thanks for joining!',
        'thecompmodels@gmail.com',
        [customer.user.email],
        fail_silently=False)


webhook_map = {
    'invoice.payment_failed': invoice_payment_failed,
    'customer.created': customer_created}


def process_event(stripe_event):
    start = time.time()
    print('got event: ')
    print(stripe_event)
    customer = get_customer_from_event(stripe_event)
    event = Event.construct(stripe_event, customer=customer)
    
    func = webhook_map.get(event.kind, None)
    if func is not None:
        func(event)
    
    total_time = time.time() - start
    print(f'done {total_time}')