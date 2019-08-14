import json

import pytest

from rest_framework.test import APIRequestFactory, force_authenticate

from webapp.apps.users.models import Project

from webapp.apps.comp.asyncsubmit import SubmitInputs, SubmitSim
from webapp.apps.comp.displayer import Displayer
from webapp.apps.comp.ioutils import get_ioutils
from webapp.apps.comp.models import Inputs, Simulation
from webapp.apps.comp.parser import APIParser

# from webapp.apps.comp.tests.parser import LocalParser, LocalAPIParser
from .compute import MockCompute

from .mockclasses import MockModel


@pytest.fixture(params=["Used-for-testing", "Used-for-testing-sponsored-apps"])
def submit_inputs(request, db, get_inputs, meta_param_dict, profile):
    class MockDisplayer(Displayer):
        def package_defaults(self):
            return get_inputs

    project = Project.objects.get(title=request.param)
    ioutils = get_ioutils(project, Displayer=MockDisplayer, Parser=APIParser)

    factory = APIRequestFactory()
    data = {
        "meta_parameters": {"metaparam": 3},
        "adjustment": {"majorsection1": {"intparam": 2}},
    }
    mockrequest = factory.post(
        "/modeler/Used-for-testing/api/v1/", data=data, format="json"
    )
    mockrequest.user = profile.user
    mockrequest.data = data

    compute = MockCompute()
    return SubmitInputs(mockrequest, project, ioutils, compute)


@pytest.fixture
def submit_sim(db, submit_inputs):
    compute = MockCompute()
    result = submit_inputs.submit()
    submit_sim = SubmitSim(result, compute, sim=None)
    return submit_inputs, submit_sim


def test_submit_inputs(db, submit_inputs):
    result = submit_inputs.submit()
    inputs = Inputs.objects.get(pk=result.pk)
    assert inputs.meta_parameters
    assert inputs.adjustment
    assert inputs.errors_warnings
    assert inputs.project
    assert inputs.owner
    assert inputs.job_id
    assert not hasattr(inputs, "outputs")


def test_submit_outputs(db, submit_sim):
    submit_inputs, submit_sim = submit_sim
    result = submit_sim.submit()
    assert result.status == "PENDING"
    assert result.inputs == submit_inputs.inputs
    assert result.job_id != submit_inputs.inputs.job_id
    assert result.sponsor == result.project.sponsor
