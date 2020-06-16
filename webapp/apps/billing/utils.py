import json

from webapp.apps.users.models import Project
from .models import SubscriptionItem, UsageRecord, Plan


class ChargeRunMixin:
    """
    Add charge_run method to outputs view. This class makes it easy to test
    the logic for charging users for model runs.
    """

    def charge_run(self, sim, meta_dict, use_stripe=True):
        sim.run_time = sum(meta_dict["task_times"])
        sim.run_cost = sim.project.run_cost(sim.run_time)
        if use_stripe and sim.project.pay_per_sim:
            quantity = sim.project.run_cost(sim.run_time, adjust=True)
            plan = sim.project.product.plans.get(usage_type="metered")
            # The sponsor is also stored on the Simulation object. However, the
            # Project object should be considered the single source of truth
            # for sending usage records.
            sponsor = sim.project.sponsor
            if sponsor is not None:
                customer = sponsor.user.customer
            else:
                customer = sim.owner.user.customer
            try:
                si = SubscriptionItem.objects.get(
                    subscription__customer=customer, plan=plan
                )
            except SubscriptionItem.DoesNotExist:
                customer.sync_subscriptions(plans=Plan.objects.filter(pk=plan.pk))
                si = SubscriptionItem.objects.get(
                    subscription__customer=customer, plan=plan
                )
            stripe_ur = UsageRecord.create_stripe_object(
                quantity=Project.dollar_to_penny(quantity),
                timestamp=None,
                subscription_item=si,
            )
            UsageRecord.construct(stripe_ur, si)


def has_payment_method(user):
    return hasattr(user, "customer") and user.customer is not None
