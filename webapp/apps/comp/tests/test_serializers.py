import copy
import datetime

from rest_framework.test import APIRequestFactory

from webapp.apps.users.models import User, Profile, create_profile_from_user

from webapp.apps.comp.models import ANON_BEFORE, PendingPermission
from webapp.apps.comp.serializers import (
    InputsSerializer,
    SimulationSerializer,
    MiniSimulationSerializer,
)

from .utils import _submit_inputs, _submit_sim


def test_owner_unsigned(db, get_inputs, meta_param_dict):
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

    # get_owner gives "unsigned" before ANON_BEFORE
    sim.creation_date = ANON_BEFORE - datetime.timedelta(days=2)
    sim.save()
    assert sim.get_owner() == "unsigned"

    data = SimulationSerializer(instance=sim).data
    assert data["owner"] == "unsigned"
    data = MiniSimulationSerializer(instance=sim).data
    assert data["owner"] == "unsigned"


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
    assert "pending_permissions" not in data
    data = SimulationSerializer(instance=sim, context={"request": req}).data
    assert data["has_write_access"] == True
    assert "pending_permissions" in data

    data = InputsSerializer(instance=sim.inputs).data
    assert data["has_write_access"] == False
    data = InputsSerializer(instance=sim.inputs, context={"request": req}).data
    assert data["has_write_access"] == True


def test_authors_sorted_alphabetically(db, get_inputs, meta_param_dict):
    modeler = User.objects.get(username="modeler").profile
    inputs = _submit_inputs("Used-for-testing", get_inputs, meta_param_dict, modeler)

    _, submit_sim = _submit_sim(inputs)
    sim = submit_sim.submit()
    sim.status = "SUCCESS"
    sim.save()

    factory = APIRequestFactory()
    req = factory.get("/")
    req.user = modeler.user

    u = User.objects.create_user("aaaa", "aaaa@example.com", "heyhey2222")
    create_profile_from_user(u)
    profile = Profile.objects.get(user__username="aaaa")

    pp = PendingPermission.objects.create(
        sim=sim, profile=profile, permission_name="add_author"
    )
    pp.add_author()

    data = SimulationSerializer(instance=sim, context={"request": req}).data
    data2 = copy.deepcopy(data)
    assert sorted(data2["authors"]) == data["authors"]

    data = SimulationSerializer(instance=sim, context={"request": req}).data
    data2 = copy.deepcopy(data)
    assert sorted(data2["authors"]) == data["authors"]

    data = InputsSerializer(instance=sim.inputs, context={"request": req}).data
    data2 = copy.deepcopy(data)
    assert sorted(data2["sim"]["authors"]) == data["sim"]["authors"]
