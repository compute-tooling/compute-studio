import json
import os

from webapp.apps.users.models import Project
from .models import SubscriptionItem, UsageRecord


USE_STRIPE = os.environ.get("USE_STRIPE", "false").lower() == "true"


def get_billing_data(include_mock_data=False):
    path = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(path, "billing.json")) as f:
        billing = json.loads(f.read())
    if include_mock_data:
        with open(os.path.join(path, "tests", "mock-billing.json")) as f:
            billing.update(json.loads(f.read()))
    return billing


class ChargeRunMixin:
    """
    Add charge_run method to outputs view. This class makes it easy to test
    the logic for charging users for model runs.
    """

    def charge_run(self, meta_dict, use_stripe=True):
        self.object.run_time = sum(meta_dict["task_times"])
        self.object.run_cost = self.object.project.run_cost(self.object.run_time)
        if use_stripe:
            quantity = self.object.project.run_cost(self.object.run_time, adjust=True)
            plan = self.object.project.product.plans.get(usage_type="metered")
            # The sponsor is also stored on the Simulation object. However, the
            # Project object should be considered the single source of truth
            # for sending usage records.
            sponsor = self.object.project.sponsor
            if sponsor is not None:
                customer = sponsor.user.customer
            else:
                customer = self.object.owner.user.customer
            si = SubscriptionItem.objects.get(
                subscription__customer=customer, plan=plan
            )
            stripe_ur = UsageRecord.create_stripe_object(
                quantity=Project.dollar_to_penny(quantity),
                timestamp=None,
                subscription_item=si,
            )
            UsageRecord.construct(stripe_ur, si)
