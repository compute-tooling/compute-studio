import json

import pytest


from webapp.apps.comp.models import Inputs, Simulation
from .utils import _submit_inputs, _submit_sim


@pytest.fixture(params=["Used-for-testing", "Used-for-testing-sponsored-apps"])
def submit_inputs(request, db, get_inputs, meta_param_dict, profile):
    return _submit_inputs(request.param, get_inputs, meta_param_dict, profile)


@pytest.fixture
def submit_sim(db, submit_inputs):
    return _submit_sim(submit_inputs)


def test_submit_inputs(db, submit_inputs):
    result = submit_inputs.submit()
    inputs = Inputs.objects.get(pk=result.pk)
    assert inputs.meta_parameters
    assert inputs.adjustment
    assert inputs.errors_warnings
    assert inputs.project
    assert inputs.owner
    assert inputs.job_id
    assert inputs.sim
    assert inputs.status == "PENDING"
    assert inputs.sim.status == "STARTED"


def test_submit_outputs(db, submit_sim):
    submit_inputs, submit_sim = submit_sim
    result = submit_sim.submit()
    assert result.status == "PENDING"
    assert result.inputs == submit_inputs.inputs
    assert result.job_id != submit_inputs.inputs.job_id
    assert result.sponsor == result.project.sponsor


def test_parents_submit(db, get_inputs, meta_param_dict, profile):
    inputs = _submit_inputs("Used-for-testing", get_inputs, meta_param_dict, profile)

    submit_inputs0, submit_sim0 = _submit_sim(inputs)
    _ = submit_sim0.submit()
    submit_sim0.sim.title = "hello world"
    submit_sim0.sim.save()

    assert submit_inputs0.inputs.parent_sim == None
    assert submit_sim0.sim.parent_sim == None

    inputs = _submit_inputs(
        "Used-for-testing",
        get_inputs,
        meta_param_dict,
        profile,
        parent_model_pk=submit_sim0.sim.model_pk,
    )

    submit_inputs1, submit_sim1 = _submit_sim(inputs)
    _ = submit_sim1.submit()

    assert submit_inputs1.inputs.parent_sim == submit_sim0.sim
    assert submit_sim1.sim.parent_sim == submit_sim0.sim
    assert submit_sim1.sim.title == "hello world"


@pytest.mark.parametrize("notify_on_completion", [True, False])
def test_set_notification_on_completion(
    db, get_inputs, meta_param_dict, profile, notify_on_completion
):
    inputs = _submit_inputs(
        "Used-for-testing",
        get_inputs,
        meta_param_dict,
        profile,
        notify_on_completion=notify_on_completion,
    )
    inputs.submit()

    assert inputs.sim.notify_on_completion is notify_on_completion

    sim = Simulation.objects.get(pk=inputs.sim.pk)
    assert sim.notify_on_completion is notify_on_completion
