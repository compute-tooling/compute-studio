"""
Create invoices for previous month's usage.

- For each customer:
  - Loop over all simulations that they own or sponsored.
    - Sum time * price / sec
  - Loop over all deployments where they own the embed approval or are owners.
    - Sum length of deployment * price / sec
"""
import math
import os
from collections import defaultdict
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from webapp.apps.billing.models import Customer

import stripe

stripe.api_key = os.environ.get("STRIPE_SECRET")


def process_simulations(simulations):
    results = defaultdict(list)
    for simulation in simulations.all():
        project = simulation.project
        if getattr(simulation, "tag"):
            server_cost = simulation.tag.server_cost
        else:
            server_cost = project.server_cost
        run_time = simulation.run_time

        if run_time <= 0:
            continue

        results[str(project)].append(
            {
                "model_pk": simulation.model_pk,
                "server_cost": server_cost,
                "run_time": run_time,
            }
        )

    return results


def process_deployments(deployments):
    results = defaultdict(list)
    for deployment in deployments:
        project = deployment.project
        if getattr(deployment, "tag"):
            server_cost = deployment.tag.server_cost
        else:
            server_cost = project.server_cost

        run_time = (deployment.deleted_at - deployment.created_at).seconds

        if run_time <= 0:
            continue

        results[str(project)].append(
            {
                "deployment_id": deployment.id,
                "server_cost": server_cost,
                "run_time": run_time,
            }
        )

    return results


def aggregate_metrics(grouped):
    results = {}
    for project, metrics in grouped.items():
        results[project] = {
            "n": len(metrics),
            "total_cost": sum(
                metric["server_cost"] * metric["run_time"] / 3600 for metric in metrics
            ),
            "total_time": sum(metric["run_time"] for metric in metrics) / 3600,
        }
    return results


def create_invoice_items(customer, aggregated_metrics, description, period):
    for name, metrics in aggregated_metrics.items():
        n, total_cost, total_time = (
            metrics["n"],
            metrics["total_cost"],
            metrics["total_time"],
        )
        total_time_mins = round(total_time * 60, 2)
        stripe.InvoiceItem.create(
            customer=customer.stripe_id,
            amount=int(total_cost * 100),
            description=f"{name} ({n} {description} totalling {total_time_mins} minutes)",
            period=period,
            currency="usd",
        )


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        start = timezone.make_aware(datetime.fromisoformat("2020-08-01"))
        end = timezone.now()
        for customer in Customer.objects.all():
            if not customer.user:
                # print("customer", customer)
                continue
            profile = customer.user.profile
            owner_sims = process_simulations(
                profile.sims.filter(sponsor__isnull=True, creation_date__gte=start)
            )
            sponsor_sims = process_simulations(
                customer.user.profile.sponsored_sims.filter(creation_date__gte=start)
            )

            owner_sim_costs = aggregate_metrics(owner_sims)
            sponsor_sim_costs = aggregate_metrics(sponsor_sims)

            ea_deployments = process_deployments(
                profile.deployments.filter(
                    embed_approval__owner=profile,
                    created_at__gte=start,
                    deleted_at__lte=end,
                )
            )

            # same as sponsored for now.
            owner_deployments = process_deployments(
                profile.deployments.filter(
                    owner=profile,
                    embed_approval__isnull=True,
                    created_at__gte=start,
                    deleted_at__lte=end,
                )
            )

            ea_deployment_costs = aggregate_metrics(ea_deployments)
            owner_deployment_costs = aggregate_metrics(owner_deployments)

            print(profile)
            print(owner_sim_costs)
            print(sponsor_sim_costs)
            print(ea_deployment_costs)
            print(owner_deployment_costs)

            create_invoice = (
                bool(owner_sim_costs)
                or bool(sponsor_sim_costs)
                or bool(ea_deployment_costs)
                or bool(owner_deployment_costs)
            )

            if not create_invoice:
                continue

            start_ts = math.floor(start.timestamp())
            end_ts = math.floor(end.timestamp())

            period = {"start": start_ts, "end": end_ts}

            create_invoice_items(customer, owner_sim_costs, "simulations", period)
            create_invoice_items(
                customer, sponsor_sim_costs, "sponsored simulations", period
            )
            create_invoice_items(
                customer, ea_deployment_costs, "embedded deployments", period
            )
            create_invoice_items(
                customer, owner_deployment_costs, "sponsored deployments", period
            )

            print("creating invoice for ", customer, customer.user.profile)
            stripe.Invoice.create(
                customer=customer.stripe_id,
                description="Compute Studio Usage Subscription",
            )
