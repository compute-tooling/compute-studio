import pytest

from hashids import Hashids

from django.http import Http404
from django.contrib import auth

from webapp.settings import INPUTS_SALT
from webapp.apps.users.models import Project, Profile

from webapp.apps.comp.models import Inputs, Simulation

from .test_asyncsubmit import _submit_inputs, _submit_sim


User = auth.get_user_model()


def test_get_next_model_pk(db):
    owner = Profile.objects.get(user__username="modeler")
    project = Project.objects.get(title="Used-for-testing", owner=owner)
    inputs = Inputs(inputs_style="paramtools", project=project)
    inputs.save()
    naive_next_model_pk = 1
    for sim in Simulation.objects.filter(project=project):
        if sim.model_pk >= naive_next_model_pk:
            naive_next_model_pk = sim.model_pk
    sim = Simulation(
        inputs=inputs,
        project=project,
        model_pk=Simulation.objects.next_model_pk(project),
    )
    sim.save()
    assert sim.model_pk == naive_next_model_pk
    assert Simulation.objects.next_model_pk(project) == sim.model_pk + 1


def test_hashids(db, test_models):
    hashids = Hashids(salt=INPUTS_SALT, min_length=6)
    inputs = test_models[0].inputs
    pk = inputs.pk
    hashid = hashids.encode(pk)

    # test get_hashid returns encoded pk and encoded pk
    # can be used to return the correct inputs object.
    assert hashid == inputs.get_hashid()
    assert Inputs.objects.from_hashid(hashid) == inputs
    assert Inputs.objects.get_object_from_hashid_or_404(hashid) == inputs

    # Test situation where item cannot be encoded to a number
    # and situation where pk does not exist.
    assert Inputs.objects.from_hashid("a") == None
    with pytest.raises(Inputs.DoesNotExist):
        Inputs.objects.from_hashid(hashids.encode(1000))

    with pytest.raises(Http404):
        Inputs.objects.get_object_from_hashid_or_404(hashids.encode(1000))
    with pytest.raises(Http404):
        Inputs.objects.get_object_from_hashid_or_404("a")


def test_parent_sims(db, get_inputs, meta_param_dict, profile):
    modeler = User.objects.get(username="modeler").profile
    inputs = _submit_inputs("Used-for-testing", get_inputs, meta_param_dict, modeler)

    sims = []
    for i in range(0, 10):
        submit_inputs, submit_sim = _submit_sim(inputs)
        sims.append(submit_sim.submit())
        inputs = _submit_inputs(
            "Used-for-testing",
            get_inputs,
            meta_param_dict,
            profile if i % 3 else modeler,  # swap profiles every three sims.
            parent_model_pk=sims[-1].model_pk,
        )

    child_sim = sims[-1]
    assert child_sim.parent_sims() == list(reversed(sims))

    init_sim = sims[0]
    assert init_sim.parent_sims() == [init_sim]

    for ix in range(1, 10):
        middle_sim = sims[ix]
        assert middle_sim.parent_sims() == list(reversed(sims[: ix + 1]))
