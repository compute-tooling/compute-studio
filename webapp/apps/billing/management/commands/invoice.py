"""
Create invoices for previous month's usage.

- For each customer:
  - Loop over all simulations that they own or sponsored.
    - Sum time * price / sec
  - Loop over all deployments where they own the embed approval or are owners.
    - Sum length of deployment * price / sec
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from webapp.apps.billing.models import Customer
from webapp.apps.billing.invoice import invoice_customer


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        start = timezone.make_aware(datetime.fromisoformat("2019-08-01"))
        end = timezone.now()
        for customer in Customer.objects.all():
            if not customer.user:
                # print("customer", customer)
                continue
            invoice_customer(customer, start, end, send_invoice=False)
