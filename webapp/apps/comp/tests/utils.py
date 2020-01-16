import os

from rest_framework.test import APIRequestFactory

from webapp.apps.users.models import Project
from webapp.apps.comp.asyncsubmit import SubmitInputs, SubmitSim
from webapp.apps.comp.displayer import Displayer
from webapp.apps.comp.ioutils import get_ioutils
from webapp.apps.comp.models import Simulation
from webapp.apps.comp.parser import APIParser

from .compute import MockCompute


def read_outputs(outputs_name):
    curr = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(curr, f"{outputs_name}.json"), "r") as f:
        outputs = f.read()
    return outputs


def _submit_inputs(title, get_inputs, meta_param_dict, profile, parent_model_pk=None):
    class MockDisplayer(Displayer):
        def package_defaults(self):
            return get_inputs

    project = Project.objects.get(title=title)
    ioutils = get_ioutils(project, Displayer=MockDisplayer, Parser=APIParser)

    factory = APIRequestFactory()
    data = {
        "meta_parameters": {"metaparam": 3},
        "adjustment": {"majorsection1": {"intparam": 2}},
    }
    if parent_model_pk is not None:
        data["parent_model_pk"] = parent_model_pk
    mockrequest = factory.post(
        "/modeler/Used-for-testing/api/v1/", data=data, format="json"
    )
    mockrequest.user = profile.user
    mockrequest.data = data

    sim = Simulation.objects.new_sim(profile.user, project)

    compute = MockCompute()
    return SubmitInputs(mockrequest, project, ioutils, compute, sim)


def _submit_sim(submit_inputs):
    compute = MockCompute()
    result = submit_inputs.submit()
    submit_sim = SubmitSim(result.sim, compute)
    return submit_inputs, submit_sim
