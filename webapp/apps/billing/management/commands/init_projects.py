from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from webapp.apps.billing.models import (Project, Product, Plan)
from webapp.apps.billing.utils import get_billing_data

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            '--use_stripe',
            action='store_true',
            dest='use_stripe',
            help='Use stripe when initializing the database',
        )

    def handle(self, *args, **options):
        use_stripe = options["use_stripe"]
        billing = get_billing_data()
        for app_name, plan in billing.items():
            try:
                profile = User.objects.get(username=plan["username"]).profile
            except User.DoesNotExist:
                profile = None
            project, _ = Project.objects.update_or_create(
                name=plan['name'],
                defaults={'server_cost': plan['server_cost'],
                          'exp_task_time': plan['exp_task_time'],
                          'exp_num_tasks': plan['exp_num_tasks'],
                          'is_public': plan['is_public'],
                          'profile': profile})
            if use_stripe:
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
