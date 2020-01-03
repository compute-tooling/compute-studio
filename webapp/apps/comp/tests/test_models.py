import pytest

from hashids import Hashids

from django.http import Http404
from django.contrib import auth
from django.forms.models import model_to_dict

from webapp.settings import INPUTS_SALT
from webapp.apps.users.models import Project, Profile

from webapp.apps.comp.models import Inputs, Simulation, ForkObjectException

from .test_asyncsubmit import _submit_inputs, _submit_sim


User = auth.get_user_model()


def test_new_sim(db, profile):
    project = Project.objects.get(
        title="Used-for-testing", owner__user__username="modeler"
    )
    sim = Simulation.objects.new_sim(profile.user, project)
    assert sim
    assert sim.inputs


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
    assert child_sim.parent_sims() == list(reversed(sims[:-1]))

    init_sim = sims[0]
    assert init_sim.parent_sims() == []

    for ix in range(1, 10):
        middle_sim = sims[ix]
        assert middle_sim.parent_sims() == list(reversed(sims[:ix]))


def test_sim_fork(db, get_inputs, meta_param_dict, profile):
    modeler = User.objects.get(username="modeler").profile
    inputs = _submit_inputs("Used-for-testing", get_inputs, meta_param_dict, modeler)

    sims = []
    submit_inputs, submit_sim = _submit_sim(inputs)
    sim = submit_sim.submit()

    sim.inputs.status = "SUCCESS"
    sim.inputs.save()

    sim.outputs = "hello world"
    sim.status = "SUCCESS"
    sim.save()

    next_model_pk = Simulation.objects.next_model_pk(sim.project)
    newsim = Simulation.objects.fork(sim, profile.user)
    assert newsim.owner != sim.owner
    assert newsim.inputs.owner == newsim.owner and newsim.inputs.owner != sim.owner
    assert newsim.model_pk == next_model_pk
    assert float(newsim.run_cost) == 0.0
    assert newsim.parent_sim == newsim.inputs.parent_sim == sim

    def objects_eq(obj1, obj2, fields_to_exclude):
        data1 = model_to_dict(obj1)
        data2 = model_to_dict(obj2)
        for field in data1:
            if field in fields_to_exclude:
                continue
            assert data1[field] == data2[field]


    fields_to_exclude = ["id", "owner", "job_id", "parent_sim"]
    objects_eq(sim.inputs, newsim.inputs, fields_to_exclude)

    fields_to_exclude += ["inputs", "run_cost", "model_pk"]
    objects_eq(sim, newsim, fields_to_exclude)

    sim.status = "PENDING"
    sim.save()
    with pytest.raises(ForkObjectException):
        Simulation.objects.fork(sim, profile.user)

    sim.inputs.status = "PENDING"
    sim.inputs.save()
    with pytest.raises(ForkObjectException):
        Simulation.objects.fork(sim, profile.user)