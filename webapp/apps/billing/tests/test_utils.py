import pytest

from django.contrib.auth import get_user_model

from webapp.apps.billing.utils import has_payment_method, ChargeRunMixin
from webapp.apps.billing.models import UsageRecord
from webapp.apps.comp.models import Inputs, Simulation
from webapp.apps.users.models import Profile, Project

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
