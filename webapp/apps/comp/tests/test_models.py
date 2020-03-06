import datetime
import json
import pytest

from hashids import Hashids

from django.http import Http404
from django.contrib import auth
from django.forms.models import model_to_dict
from guardian.shortcuts import get_perms

from webapp.apps.users.models import Project, Profile, create_profile_from_user

from webapp.apps.comp.models import Inputs, Simulation, PendingPermission, ANON_BEFORE
from webapp.apps.comp.exceptions import (
    ForkObjectException,
    VersionMismatchException,
    ResourceLimitException,
)

from .utils import _submit_inputs, _submit_sim, read_outputs, _shuffled_sims, Customer

User = auth.get_user_model()


@pytest.fixture
def shuffled_sims(profile, get_inputs, meta_param_dict):
    return _shuffled_sims(profile, get_inputs, meta_param_dict)


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
        sims[-1].is_public = True
        sims[-1].save()
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


def test_private_parent_sims(db, shuffled_sims, profile):
    modeler = User.objects.get(username="modeler").profile
    sims, modeler_sims, tester_sims = shuffled_sims

    child_sim = sims[-1]
    assert child_sim.parent_sims(user=None) == []
    assert child_sim.parent_sims(user=modeler.user) == list(reversed(modeler_sims))
    assert child_sim.parent_sims(user=profile.user) == list(reversed(tester_sims))


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

    # make sure each sim's owner has read access and that the
    # read access for the new sim only applies to the owner
    # of the new sim and not the owner of the old sim.
    assert newsim.has_admin_access(newsim.owner.user)
    assert sim.has_admin_access(sim.owner.user)
    newsim.is_public = False
    newsim.save()
    assert not newsim.has_read_access(sim.owner.user)

    def objects_eq(obj1, obj2, fields_to_exclude):
        data1 = model_to_dict(obj1)
        data2 = model_to_dict(obj2)
        for field in data1:
            if field in fields_to_exclude:
                continue
            assert data1[field] == data2[field]

    fields_to_exclude = ["id", "owner", "job_id", "parent_sim"]
    objects_eq(sim.inputs, newsim.inputs, fields_to_exclude)

    fields_to_exclude += ["inputs", "run_cost", "model_pk", "creation_date", "authors"]
    objects_eq(sim, newsim, fields_to_exclude)

    sim.status = "PENDING"
    sim.save()
    with pytest.raises(ForkObjectException):
        Simulation.objects.fork(sim, profile.user)

    sim.inputs.status = "PENDING"
    sim.inputs.save()
    with pytest.raises(ForkObjectException):
        Simulation.objects.fork(sim, profile.user)


def test_outputs_versions(db, get_inputs, meta_param_dict):
    modeler = User.objects.get(username="modeler").profile
    inputs = _submit_inputs("Used-for-testing", get_inputs, meta_param_dict, modeler)

    _, submit_sim = _submit_sim(inputs)
    sim = submit_sim.submit()
    sim.status = "SUCCESS"
    sim.save()

    v0_outputs = json.loads(read_outputs("Matchups_v0"))
    sim.outputs = v0_outputs
    sim.save()

    assert sim.outputs_version() == "v0"
    assert (
        sim.get_absolute_url()
        == sim.get_absolute_v0_url()
        == f"/{sim.project.owner}/{sim.project.title}/{sim.model_pk}/v0/"
    )

    v1_outputs = json.loads(read_outputs("Matchups_v1"))
    sim.outputs = v1_outputs
    sim.save()

    assert sim.outputs_version() == "v1"
    assert (
        sim.get_absolute_url()
        == f"/{sim.project.owner}/{sim.project.title}/{sim.model_pk}/"
    )

    with pytest.raises(VersionMismatchException):
        sim.get_absolute_v0_url()


def test_get_owner(db, get_inputs, meta_param_dict):
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

    # get_owner gives "unsigned" before ANON_BEFORE
    sim.creation_date = ANON_BEFORE - datetime.timedelta(days=2)
    sim.save()
    assert sim.get_owner() == "unsigned"


def test_sim_permissions(db, get_inputs, meta_param_dict, profile):
    modeler = User.objects.get(username="modeler").profile
    inputs = _submit_inputs("Used-for-testing", get_inputs, meta_param_dict, modeler)

    _, submit_sim = _submit_sim(inputs)
    sim = submit_sim.submit()
    sim.status = "SUCCESS"
    sim.save()

    # check permissions for owner and random profile
    assert get_perms(sim.owner.user, sim) == ["admin_simulation"]
    assert sim.role(sim.owner.user) == "admin"
    assert get_perms(profile.user, sim) == []
    assert sim.role(profile.user) is None

    # sim owner has all levels of access
    assert (
        sim.is_owner(sim.owner.user)
        and sim.has_admin_access(sim.owner.user)
        and sim.has_write_access(sim.owner.user)
        and sim.has_read_access(sim.owner.user)
    )
    # random user has no access
    assert (
        not sim.is_owner(profile.user)
        and not sim.has_admin_access(profile.user)
        and not sim.has_write_access(profile.user)
        and not sim.has_read_access(profile.user)
    )
    # None has no access and does not cause errors
    assert (
        not sim.is_owner(None)
        and not sim.has_admin_access(None)
        and not sim.has_write_access(None)
        and not sim.has_read_access(None)
    )

    # test grant/removal of read access.
    sim.grant_read_permissions(profile.user)
    assert (
        get_perms(profile.user, sim) == ["read_simulation"]
        and sim.role(profile.user) == "read"
    )
    assert (
        not sim.is_owner(profile.user)
        and not sim.has_admin_access(profile.user)
        and not sim.has_write_access(profile.user)
        and sim.has_read_access(profile.user)
    )
    sim.remove_permissions(profile.user)
    assert get_perms(profile.user, sim) == [] and sim.role(profile.user) is None
    assert (
        not sim.is_owner(profile.user)
        and not sim.has_admin_access(profile.user)
        and not sim.has_write_access(profile.user)
        and not sim.has_read_access(profile.user)
    )

    # test grant/remove are idempotent:
    for _ in range(3):
        sim.grant_read_permissions(profile.user)
        assert sim.has_read_access(profile.user)
    for _ in range(3):
        sim.remove_permissions(profile.user)
        assert not sim.has_read_access(profile.user)

    # test that only one permission is applied at a time.
    sim.grant_read_permissions(profile.user)
    assert get_perms(profile.user, sim) == ["read_simulation"]
    sim.grant_write_permissions(profile.user)
    assert get_perms(profile.user, sim) == ["write_simulation"]
    sim.grant_admin_permissions(profile.user)
    assert get_perms(profile.user, sim) == ["admin_simulation"]

    sim.is_public = True
    sim.save()
    assert sim.has_read_access(modeler.user)
    assert sim.has_read_access(profile.user)
    assert sim.has_read_access(None) is True

    # test role
    sim.is_public = False
    sim.save()
    sim.assign_role("admin", profile.user)
    assert sim.has_admin_access(profile.user) and sim.role(profile.user) == "admin"
    sim.assign_role("write", profile.user)
    assert sim.has_write_access(profile.user) and sim.role(profile.user) == "write"
    sim.assign_role("read", profile.user)
    assert sim.has_read_access(profile.user) and sim.role(profile.user) == "read"
    sim.assign_role(None, profile.user)
    assert not sim.has_read_access(profile.user) and sim.role(profile.user) == None

    with pytest.raises(ValueError) as e:
        sim.assign_role("dne", profile.user)


def test_add_authors(db, get_inputs, meta_param_dict, profile):
    modeler = User.objects.get(username="modeler").profile
    inputs = _submit_inputs("Used-for-testing", get_inputs, meta_param_dict, modeler)

    _, submit_sim = _submit_sim(inputs)
    sim = submit_sim.submit()
    sim.status = "SUCCESS"
    sim.save()

    assert not sim.has_read_access(profile.user)

    # Create new pending permission object and make sure that read access was
    # granted appropriately.
    pp, created = PendingPermission.objects.get_or_create(
        sim=sim, profile=profile, permission_name="add_author"
    )
    assert created
    assert not pp.is_expired()
    assert sim.has_read_access(profile.user)
    assert get_perms(profile.user, sim) == ["read_simulation"]

    sim = Simulation.objects.get(pk=sim.pk)
    assert sim.pending_permissions.filter(id=pp.id).count() == 1

    assert sim.authors.all().count() == 1 and sim.authors.get(pk=modeler.pk)

    pp.add_author()

    sim = Simulation.objects.get(pk=sim.pk)
    assert sim.authors.all().count() == 2 and sim.authors.get(pk=profile.pk) == profile

    assert PendingPermission.objects.filter(id=pp.id).count() == 0


def test_public_sims(db, shuffled_sims, profile):
    # modeler = User.objects.get(username="modeler").profile
    _, modeler_sims, _ = shuffled_sims

    for sim in modeler_sims:
        sim.is_public = True
        sim.save()

    assert set(Simulation.objects.public_sims()) == set(modeler_sims)

    modeler_sims[1].creation_date = ANON_BEFORE - datetime.timedelta(days=2)
    modeler_sims[1].save()
    assert set(Simulation.objects.public_sims()) == set(
        [modeler_sims[0]] + modeler_sims[2:]
    )


def test_collaborator_limit_triggered(
    db, get_inputs, meta_param_dict, free_profile, profile
):
    inputs = _submit_inputs(
        "Used-for-testing", get_inputs, meta_param_dict, free_profile
    )

    _, submit_sim = _submit_sim(inputs)
    sim = submit_sim.submit()
    sim.status = "SUCCESS"
    sim.save()

    # test grant/removal of read access.
    sim.assign_role("read", profile.user)
    assert (
        get_perms(profile.user, sim) == ["read_simulation"]
        and sim.role(profile.user) == "read"
    )

    u = User.objects.create_user("second-collab", "second@example.com", "heyhey2222")
    create_profile_from_user(u)

    with pytest.raises(ResourceLimitException) as excinfo:
        sim.assign_role("read", u)

    assert str(excinfo.value) == ResourceLimitException.collaborators_msg
    assert get_perms(u, sim) == [] and sim.role(u) == None


def test_collaborator_limit_passes(
    db, get_inputs, meta_param_dict, pro_profile, profile
):
    inputs = _submit_inputs(
        "Used-for-testing", get_inputs, meta_param_dict, pro_profile
    )

    _, submit_sim = _submit_sim(inputs)
    sim = submit_sim.submit()
    sim.status = "SUCCESS"
    sim.save()

    # test grant/removal of read access.
    sim.assign_role("read", profile.user)
    assert (
        get_perms(profile.user, sim) == ["read_simulation"]
        and sim.role(profile.user) == "read"
    )

    u = User.objects.create_user("second-collab", "second@example.com", "heyhey2222")
    create_profile_from_user(u)

    sim.assign_role("read", u)
