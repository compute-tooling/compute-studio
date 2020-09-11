"""
Create invoices for previous month's usage.

- For each customer:
  - Loop over all simulations that they own or sponsored.
    - Sum time * price / sec
  - Loop over all deployments where they own the embed approval or are owners.
    - Sum length of deployment * price / sec
"""
import calendar
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from webapp.apps.billing.models import Customer
from webapp.apps.billing.invoice import invoice_customer


def parse_date(date_str):
    return timezone.make_aware(datetime.fromisoformat(date_str))


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def add_arguments(self, parser):
        parser.add_argument("--start")
        parser.add_argument("--end")
        parser.add_argument("--dryrun", action="store_true")

    def handle(self, *args, **options):
        print(options)
        if options.get("start"):
            start = parse_date(options["start"])
        else:
            start = timezone.now().replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
        if options.get("end"):
            end = parse_date(options["end"])
        else:
            _, end_day = calendar.monthrange(start.year, start.month)
            end = start.replace(day=end_day)
        print(f"Billing period: {str(start.date())} to {str(end.date())}")
        for customer in Customer.objects.all():
            if not customer.user:
                # print("customer", customer)
                continue
            invoice_customer(customer, start, end, send_invoice=not options["dryrun"])
