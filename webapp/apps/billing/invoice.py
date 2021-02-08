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
from pprint import pprint

from django.utils import timezone

from webapp.apps.billing.models import Customer

import stripe

stripe.api_key = os.environ.get("STRIPE_SECRET")


def process_simulations(simulations):
    results = defaultdict(list)
    for simulation in simulations.all():
        project = simulation.project
        # Project is deleted.
        if project is None:
            continue
        # Projects not doing pay per sim are handled elsewhere.
        if not project.pay_per_sim:
            continue

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
        # Projects not doing pay per sim are handled elsewhere.
        if not project.pay_per_sim:
            continue

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
            "total_cost": round(
                sum(
                    metric["server_cost"] * metric["run_time"] / 3600
                    for metric in metrics
                ),
                4,
            ),
            "total_time": round(sum(metric["run_time"] for metric in metrics) / 60, 4),
        }
    return results


def create_invoice_items(customer, aggregated_metrics, description, period):
    for project, metrics in aggregated_metrics.items():
        n, total_cost, total_time = (
            metrics["n"],
            metrics["total_cost"],
            metrics["total_time"],
        )
        if total_time > 60:
            time_msg = f"{round(total_time / 60, 2)} hours"
        else:
            time_msg = f"{int(round(total_time, 1))} minutes"
        stripe.InvoiceItem.create(
            customer=customer.stripe_id,
            amount=int(total_cost * 100),
            description=f"{project} ({n} {description} totalling {time_msg})",
            period=period,
            currency="usd",
            metadata={"project": project, "description": description},
        )


def invoice_customer(customer, start, end, send_invoice=True):
    profile = customer.user.profile
    owner_sims = process_simulations(
        profile.sims.filter(
            sponsor__isnull=True,
            creation_date__date__gte=start.date(),
            creation_date__date__lte=end.date(),
        )
    )
    sponsor_sims = process_simulations(
        customer.user.profile.sponsored_sims.filter(
            creation_date__date__gte=start.date(), creation_date__date__lte=end.date()
        )
    )

    owner_sim_costs = aggregate_metrics(owner_sims)
    sponsor_sim_costs = aggregate_metrics(sponsor_sims)

    ea_deployments = process_deployments(
        profile.deployments.filter(
            embed_approval__owner=profile,
            deleted_at__date__gte=start.date(),
            deleted_at__date__lte=end.date(),
        )
    )

    # same as sponsored for now.
    owner_deployments = process_deployments(
        profile.deployments.filter(
            owner=profile,
            embed_approval__isnull=True,
            deleted_at__date__gte=start.date(),
            deleted_at__date__lte=end.date(),
        )
    )

    ea_deployment_costs = aggregate_metrics(ea_deployments)
    owner_deployment_costs = aggregate_metrics(owner_deployments)

    summary = {
        "detail": {
            "simulations": {"owner": owner_sims, "sponsor": sponsor_sims,},
            "deployments": {
                "owner": owner_deployments,
                "embed_approval": ea_deployments,
            },
        },
        "summary": {
            "simulations": {"owner": owner_sim_costs, "sponsor": sponsor_sim_costs,},
            "deployments": {
                "owner": owner_deployment_costs,
                "embed_approval": ea_deployment_costs,
            },
        },
    }

    print()
    print("Customer username:", profile)
    pprint(summary["summary"])

    create_invoice = (
        bool(owner_sim_costs)
        or bool(sponsor_sim_costs)
        or bool(ea_deployment_costs)
        or bool(owner_deployment_costs)
    )

    if not create_invoice:
        return summary

    start_ts = math.floor(start.timestamp())
    end_ts = math.floor(end.timestamp())

    period = {"start": start_ts, "end": end_ts}

    if send_invoice:
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
        invoice = stripe.Invoice.create(
            customer=customer.stripe_id,
            description="Compute Studio Usage Subscription",
        )
    else:
        invoice = None

    summary["invoice"] = invoice

    return summary
