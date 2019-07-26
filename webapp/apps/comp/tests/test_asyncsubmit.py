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


@pytest.fixture
def submit_inputs(db, get_inputs, meta_param_dict, profile):
    class MockDisplayer(Displayer):
        def package_defaults(self):
            return get_inputs

    project = Project.objects.get(title="Used-for-testing")
    ioutils = get_ioutils(project, Displayer=MockDisplayer, Parser=APIParser)

    factory = APIRequestFactory()
    data = {
        "meta_parameters": {"metaparam": 3},
        "adjustment": {"majorsection1": {"intparam": 2}},
    }
    request = factory.post(
        "/modeler/Used-for-testing/api/v1/", data=data, format="json"
    )
    request.user = profile.user
    request.data = data

    compute = MockCompute()
    return SubmitInputs(request, project, ioutils, compute)


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


# TODO: test with errors and sponsor v. unsponsor

# def test_submit_w_errors(db, get_inputs, meta_param_dict, profile):
#     mock_errors_warnings = {
#         "majorsection1": {"errors": {"intparam": ["an error"]}, "warnings": {}}
#     }
#     project = Project.objects.get(title="Used-for-testing")
#     ioutils = get_ioutils(
#         project, Displayer=MockDisplayer, Parser=MockParser, Param=Param
#     )

#     factory = RequestFactory()
#     data = {"has_errors": ["False"], "metaparam": ["3"], "intparam": ["1"]}
#     request = factory.post("/modeler/Used-for-testing/sim", data)
