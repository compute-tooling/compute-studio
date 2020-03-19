import os

from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from webapp.apps.users.models import Project, Profile, create_profile_from_user
from webapp.apps.comp.asyncsubmit import SubmitInputs, SubmitSim
from webapp.apps.comp.displayer import Displayer
from webapp.apps.comp.ioutils import get_ioutils
from webapp.apps.comp.models import Simulation
from webapp.apps.comp.parser import APIParser

from .compute import MockCompute


User = get_user_model()


def read_outputs(outputs_name):
    curr = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(curr, f"{outputs_name}.json"), "r") as f:
        outputs = f.read()
    return outputs


def _submit_inputs(
    title,
    get_inputs,
    meta_param_dict,
    profile,
    parent_model_pk=None,
    notify_on_completion=None,
):
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
    if notify_on_completion is not None:
        data["notify_on_completion"] = notify_on_completion

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


def _shuffled_sims(profile, get_inputs, meta_param_dict):
    modeler = User.objects.get(username="modeler").profile
    # inputs = _submit_inputs("Used-for-testing", get_inputs, meta_param_dict, modeler)

    sims = []
    modeler_sims = []
    tester_sims = []
    number_sims = 10
    for i in range(0, number_sims):
        inputs = _submit_inputs(
            "Used-for-testing",
            get_inputs,
            meta_param_dict,
            profile if i % 3 else modeler,  # swap profiles every three sims.
            parent_model_pk=sims[-1].model_pk if sims else None,
        )
        _, submit_sim = _submit_sim(inputs)
        sim = submit_sim.submit()
        sims.append(sim)
        if i != number_sims - 1 and sim.owner == modeler:
            modeler_sims.append(sim)
        elif i != number_sims - 1 and sim.owner == profile:
            tester_sims.append(sim)
    return sims, modeler_sims, tester_sims


class Customer:
    def __init__(self, current_plan):
        self._current_plan = current_plan

    def current_plan(self):
        return self._current_plan


def gen_collabs(n):
    for i in range(n):
        u = User.objects.create_user(
            f"collab-{i}", f"collab{i}@example.com", "heyhey2222"
        )
        create_profile_from_user(u)
        yield Profile.objects.get(user__username=f"collab-{i}")
