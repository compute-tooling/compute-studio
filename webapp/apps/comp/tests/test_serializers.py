import datetime

from rest_framework.test import APIRequestFactory

from webapp.apps.users.models import User
from webapp.apps.comp.models import ANON_BEFORE
from webapp.apps.comp.serializers import (
    InputsSerializer,
    SimulationSerializer,
    MiniSimulationSerializer,
)

from .utils import _submit_inputs, _submit_sim


def test_owner_anonymity(db, get_inputs, meta_param_dict):
    modeler = User.objects.get(username="modeler").profile
    inputs = _submit_inputs("Used-for-testing", get_inputs, meta_param_dict, modeler)

    _, submit_sim = _submit_sim(inputs)
    sim = submit_sim.submit()
    sim.status = "SUCCESS"
    sim.save()

    # get_owner gives sim owner after ANON_BEFORE
    sim.creation_date = ANON_BEFORE + datetime.timedelta(days=2)
    sim.save()
    assert sim.get_owner() == modeler

    data = SimulationSerializer(instance=sim).data
    assert data["owner"] == str(modeler)
    data = MiniSimulationSerializer(instance=sim).data
    assert data["owner"] == str(modeler)

    # get_owner gives "anonymous" before ANON_BEFORE
    sim.creation_date = ANON_BEFORE - datetime.timedelta(days=2)
    sim.save()
    assert sim.get_owner() == "anonymous"

    data = SimulationSerializer(instance=sim).data
    assert data["owner"] == "anonymous"
    data = MiniSimulationSerializer(instance=sim).data
    assert data["owner"] == "anonymous"


def test_write_access(db, get_inputs, meta_param_dict):
    modeler = User.objects.get(username="modeler").profile
    inputs = _submit_inputs("Used-for-testing", get_inputs, meta_param_dict, modeler)

    _, submit_sim = _submit_sim(inputs)
    sim = submit_sim.submit()
    sim.status = "SUCCESS"
    sim.save()

    factory = APIRequestFactory()
    req = factory.get("/")
    req.user = modeler.user

    data = SimulationSerializer(instance=sim).data
    assert data["has_write_access"] == False
    data = SimulationSerializer(instance=sim, context={"request": req}).data
    assert data["has_write_access"] == True

    data = InputsSerializer(instance=sim).data
    assert data["has_write_access"] == False
    data = InputsSerializer(instance=sim, context={"request": req}).data
    assert data["has_write_access"] == True
