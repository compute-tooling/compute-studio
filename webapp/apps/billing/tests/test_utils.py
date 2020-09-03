from datetime import timedelta

import pytest

from django.utils import timezone
from django.contrib.auth import get_user_model

from webapp.apps.billing.utils import (
    has_payment_method,
    ChargeRunMixin,
    ChargeDeploymentMixin,
)
from webapp.apps.billing.models import UsageRecord, SubscriptionItem
from webapp.apps.comp.models import Inputs, Simulation
from webapp.apps.users.models import Profile, Project, EmbedApproval, Deployment
from webapp.apps.users.tests.utils import mock_post_to_cluster

from .utils import gen_blank_customer

User = get_user_model()


@pytest.mark.requires_stripe
def test_has_payment_method(db, customer):
    assert has_payment_method(customer.user)

    u = User.objects.create_user(
        username="pmt-test", email="testyo@email.com", password="testtest2222"
    )
    assert not has_payment_method(u)


@pytest.mark.requires_stripe
@pytest.mark.parametrize("pay_per_sim", [True, False])
def test_pay_per_sim(db, customer, pay_per_sim):
    owner = Profile.objects.get(user__username="modeler")
    project = Project.objects.get(title="Used-for-testing", owner=owner)
    project.pay_per_sim = pay_per_sim
    project.save()
    inputs = Inputs.objects.create(inputs_style="paramtools", project=project)
    sim = Simulation.objects.create(
        inputs=inputs,
        project=project,
        model_pk=Simulation.objects.next_model_pk(project),
        owner=owner,
    )

    ur_count = UsageRecord.objects.count()

    cr = ChargeRunMixin()
    cr.charge_run(sim, {"task_times": [100]})

    if pay_per_sim:
        assert ur_count + 1 == UsageRecord.objects.count()
    else:
        assert ur_count == UsageRecord.objects.count()


@pytest.mark.requires_stripe
def test_charge_run_adds_plans(db):
    """
    Create new user and make sure that the model's plan is added with ChargeRun.
    """

    # setup
    project = Project.objects.get(title="Used-for-testing")
    profile = gen_blank_customer(
        username="no_plans", email="tester@email.com", password="heyhey2222"
    )
    inputs = Inputs.objects.create(inputs_style="paramtools", project=project)
    sim = Simulation.objects.create(
        inputs=inputs,
        project=project,
        model_pk=Simulation.objects.next_model_pk(project),
        owner=profile,
    )

    # No plans set for model right now.
    plan = project.product.plans.get(usage_type="metered")
    assert (
        SubscriptionItem.objects.filter(
            subscription__customer=profile.user.customer, plan=plan
        ).count()
        == 0
    )

    cr = ChargeRunMixin()
    cr.charge_run(sim, {"task_times": [100]})

    # model's plan has been added.
    assert (
        SubscriptionItem.objects.filter(
            subscription__customer=profile.user.customer, plan=plan
        ).count()
        == 1
    )


@pytest.mark.requires_stripe
def test_charge_run_with_sponsored_model(db):
    """
    Create new user and make sure no plans are added after running sponsored model.
    """
    # setup
    project = Project.objects.get(title="Used-for-testing-sponsored-apps")
    profile = gen_blank_customer(
        username="no_plans_sponsored", email="tester@email.com", password="heyhey2222"
    )
    inputs = Inputs.objects.create(inputs_style="paramtools", project=project)
    sim = Simulation.objects.create(
        inputs=inputs,
        project=project,
        model_pk=Simulation.objects.next_model_pk(project),
        owner=profile,
    )

    # No plans set for model.
    plan = project.product.plans.get(usage_type="metered")
    assert (
        SubscriptionItem.objects.filter(
            subscription__customer=profile.user.customer, plan=plan
        ).count()
        == 0
    )

    cr = ChargeRunMixin()
    cr.charge_run(sim, {"task_times": [100]})

    # Still no plans.
    assert (
        SubscriptionItem.objects.filter(
            subscription__customer=profile.user.customer, plan=plan
        ).count()
        == 0
    )


class TestChargeDeployments:
    def test_embed_approvals(self, db, profile):
        project = Project.objects.get(title="Test-Viz")

        ea = EmbedApproval.objects.create(
            project=project,
            owner=profile,
            url="https://embed.compute.studio",
            name="my-test-embed",
        )

        with mock_post_to_cluster():
            deployment, _ = Deployment.objects.get_or_create_deployment(
                project=project, name="my-deployment", owner=None, embed_approval=ea,
            )

        elapsed = timedelta(hours=2)
        deleted_at = timezone.now() + elapsed

        deployment.deleted_at = deleted_at
        deployment.status = "terminated"
        deployment.save()

        ur_count = UsageRecord.objects.count()

        cd = ChargeDeploymentMixin()
        cd.charge_deployment(deployment, use_stripe=True)

        si = SubscriptionItem.objects.get(
            subscription__customer=ea.owner.user.customer,
            plan=project.product.plans.get(usage_type="metered"),
        )

        assert ur_count + 1 == UsageRecord.objects.count()

        assert si.usage_records.count() == 1

        ur = si.usage_records.first()

        quantity = deployment.project.run_cost(elapsed.seconds, adjust=True)
        assert ur.quantity == quantity * 100

    def test_sponsored(self, db, profile):
        project = Project.objects.get(title="Test-Viz")
        sponsor = Profile.objects.get(user__username="sponsor")
        project.sponsor = sponsor
        project.save()

        with mock_post_to_cluster():
            deployment, _ = Deployment.objects.get_or_create_deployment(
                project=project, name="my-deployment", owner=None, embed_approval=None,
            )

        elapsed = timedelta(hours=2)
        deleted_at = timezone.now() + elapsed

        deployment.deleted_at = deleted_at
        deployment.status = "terminated"
        deployment.save()

        ur_count = UsageRecord.objects.count()

        cd = ChargeDeploymentMixin()
        cd.charge_deployment(deployment, use_stripe=True)

        si = SubscriptionItem.objects.get(
            subscription__customer=sponsor.user.customer,
            plan=project.product.plans.get(usage_type="metered"),
        )

        assert ur_count + 1 == UsageRecord.objects.count()

        assert si.usage_records.count() == 1

        ur = si.usage_records.first()

        quantity = deployment.project.run_cost(elapsed.seconds, adjust=True)
        assert ur.quantity == quantity * 100
