import datetime
import json
import pytest

from hashids import Hashids

from django.http import Http404
from django.contrib import auth
from django.forms.models import model_to_dict
from django.http.response import Http404
from guardian.shortcuts import get_perms

from webapp.apps.users.models import Project, Profile, create_profile_from_user
from webapp.apps.users.tests.utils import gen_collabs
from webapp.apps.comp.models import (
    Inputs,
    Simulation,
    PendingPermission,
    ANON_BEFORE,
    FREE_PRIVATE_SIMS,
)
from webapp.apps.comp.exceptions import (
    ForkObjectException,
    VersionMismatchException,
    PrivateSimException,
    CollaboratorLimitException,
)

from .utils import (
    _submit_inputs,
    _submit_sim,
    read_outputs,
    _shuffled_sims,
    Customer,
)

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
    """Test only able to view parent sims that user can access"""

    modeler = User.objects.get(username="modeler").profile
    sims, modeler_sims, tester_sims = shuffled_sims

    child_sim = sims[-1]

    # Test public sims are all there.
    assert child_sim.parent_sims(user=None) == list(reversed(sims))[1:]

    # Make sims private
    for sim in sims:
        sim.is_public = False
        sim.save()

    child_sim.refresh_from_db()

    assert child_sim.parent_sims(user=modeler.user) == list(
        reversed([sim for sim in modeler_sims if sim != child_sim])
    )
    assert child_sim.parent_sims(user=profile.user) == list(
        reversed([sim for sim in tester_sims if sim != child_sim])
    )


@pytest.mark.parametrize("is_public", [True, False])
def test_sim_fork(db, get_inputs, meta_param_dict, is_public):
    (profile,) = gen_collabs(1, plan="pro")
    modeler = User.objects.get(username="modeler").profile
    inputs = _submit_inputs("Used-for-testing", get_inputs, meta_param_dict, modeler)

    _, submit_sim = _submit_sim(inputs)
    sim = submit_sim.submit()

    sim.inputs.status = "SUCCESS"
    sim.inputs.save()

    sim.outputs = "hello world"
    sim.status = "SUCCESS"
    sim.is_public = is_public
    sim.save()

    next_model_pk = Simulation.objects.next_model_pk(sim.project)
    newsim = Simulation.objects.fork(sim, profile.user)
    assert newsim.owner != sim.owner
    assert newsim.inputs.owner == newsim.owner and newsim.inputs.owner != sim.owner
    assert newsim.model_pk == next_model_pk
    assert float(newsim.run_cost) == 0.0
    assert newsim.parent_sim == newsim.inputs.parent_sim == sim

    if not sim.is_public:
        # make sure each sim's owner has read access and that the
        # read access for the new sim only applies to the owner
        # of the new sim and not the owner of the old sim.
        assert newsim.has_admin_access(newsim.owner.user)
        assert sim.has_admin_access(sim.owner.user)
        assert newsim.is_public == False
        # newsim.save()
        assert not newsim.has_read_access(sim.owner.user)

    def objects_eq(obj1, obj2, fields_to_exclude):
        data1 = model_to_dict(obj1)
        data2 = model_to_dict(obj2)
        for field in data1:
            if field in fields_to_exclude:
                continue
            assert (
                data1[field] == data2[field]
            ), f"At {field}: {data1[field]} != {data2[field]}"

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


def test_sim_screenshot_query(db, get_inputs, meta_param_dict):
    modeler = User.objects.get(username="modeler").profile
    inputs = _submit_inputs("Used-for-testing", get_inputs, meta_param_dict, modeler)

    _, submit_sim = _submit_sim(inputs)
    sim = submit_sim.submit()
    sim.status = "SUCCESS"
    sim.outputs = json.loads(read_outputs("Matchups_v1"))
    sim.save()

    for output in sim.outputs["outputs"]["renderable"]["outputs"]:
        assert sim == Simulation.objects.get_object_from_screenshot(output["id"])

    with pytest.raises(Simulation.DoesNotExist):
        Simulation.objects.get_object_from_screenshot("abc123")

    with pytest.raises(Http404):
        Simulation.objects.get_object_from_screenshot("abc123", http_404_on_fail=True)


def test_sim_permissions(db, get_inputs, meta_param_dict, pro_profile):
    collab = next(gen_collabs(1))
    inputs = _submit_inputs(
        "Used-for-testing", get_inputs, meta_param_dict, pro_profile
    )

    _, submit_sim = _submit_sim(inputs)
    sim = submit_sim.submit()
    sim.status = "SUCCESS"
    sim.is_public = False
    sim.save()

    # check permissions for owner and random profile
    assert get_perms(sim.owner.user, sim) == ["admin_simulation"]
    assert sim.role(sim.owner.user) == "admin"
    assert get_perms(collab.user, sim) == []
    assert sim.role(collab.user) is None

    # sim owner has all levels of access
    assert (
        sim.is_owner(sim.owner.user)
        and sim.has_admin_access(sim.owner.user)
        and sim.has_write_access(sim.owner.user)
        and sim.has_read_access(sim.owner.user)
    )
    # random user has no access
    assert (
        not sim.is_owner(collab.user)
        and not sim.has_admin_access(collab.user)
        and not sim.has_write_access(collab.user)
        and not sim.has_read_access(collab.user)
    )
    # None has no access and does not cause errors
    assert (
        not sim.is_owner(None)
        and not sim.has_admin_access(None)
        and not sim.has_write_access(None)
        and not sim.has_read_access(None)
    )

    # test grant/removal of read access.
    sim.grant_read_permissions(collab.user)
    assert (
        get_perms(collab.user, sim) == ["read_simulation"]
        and sim.role(collab.user) == "read"
    )
    assert (
        not sim.is_owner(collab.user)
        and not sim.has_admin_access(collab.user)
        and not sim.has_write_access(collab.user)
        and sim.has_read_access(collab.user)
    )
    sim.remove_permissions(collab.user)
    assert get_perms(collab.user, sim) == [] and sim.role(collab.user) is None
    assert (
        not sim.is_owner(collab.user)
        and not sim.has_admin_access(collab.user)
        and not sim.has_write_access(collab.user)
        and not sim.has_read_access(collab.user)
    )

    # test grant/remove are idempotent:
    for _ in range(3):
        sim.grant_read_permissions(collab.user)
        assert sim.has_read_access(collab.user)
    for _ in range(3):
        sim.remove_permissions(collab.user)
        assert not sim.has_read_access(collab.user)

    # test that only one permission is applied at a time.
    sim.grant_read_permissions(collab.user)
    assert get_perms(collab.user, sim) == ["read_simulation"]
    sim.grant_write_permissions(collab.user)
    assert get_perms(collab.user, sim) == ["write_simulation"]
    sim.grant_admin_permissions(collab.user)
    assert get_perms(collab.user, sim) == ["admin_simulation"]

    sim.is_public = True
    sim.save()
    assert sim.has_read_access(pro_profile.user)
    assert sim.has_read_access(collab.user)
    assert sim.has_read_access(None) is True

    # test role
    sim.is_public = False
    sim.save()
    sim.assign_role("admin", collab.user)
    assert sim.has_admin_access(collab.user) and sim.role(collab.user) == "admin"
    sim.assign_role("write", collab.user)
    assert sim.has_write_access(collab.user) and sim.role(collab.user) == "write"
    sim.assign_role("read", collab.user)
    assert sim.has_read_access(collab.user) and sim.role(collab.user) == "read"
    sim.assign_role(None, collab.user)
    assert not sim.has_read_access(collab.user) and sim.role(collab.user) == None

    with pytest.raises(ValueError):
        sim.assign_role("dne", collab.user)


def test_add_authors(db, get_inputs, meta_param_dict, pro_profile):
    inputs = _submit_inputs(
        "Used-for-testing", get_inputs, meta_param_dict, pro_profile
    )

    _, submit_sim = _submit_sim(inputs)
    sim = submit_sim.submit()
    sim.status = "SUCCESS"
    sim.is_public = False
    sim.save()

    collab = next(gen_collabs(1))

    assert not sim.has_read_access(collab.user)

    # Create new pending permission object and make sure that read access was
    # granted appropriately.
    pp, created = PendingPermission.objects.get_or_create(
        sim=sim, profile=collab, permission_name="add_author"
    )
    assert created
    assert not pp.is_expired()
    assert sim.has_read_access(collab.user)
    assert get_perms(collab.user, sim) == ["read_simulation"]

    sim = Simulation.objects.get(pk=sim.pk)
    assert sim.pending_permissions.filter(id=pp.id).count() == 1

    assert sim.authors.all().count() == 1 and sim.authors.get(pk=pro_profile.pk)

    pp.add_author()

    sim = Simulation.objects.get(pk=sim.pk)
    assert sim.authors.all().count() == 2 and sim.authors.get(pk=collab.pk) == collab

    assert PendingPermission.objects.filter(id=pp.id).count() == 0


def test_public_sims(db, shuffled_sims, profile):
    """Make some of the sims public and ensure those can be viewed"""
    _, modeler_sims, other_sims = shuffled_sims

    for sim in other_sims:
        sim.is_public = False
        sim.save()

    assert set(Simulation.objects.public_sims()) == set(modeler_sims)

    modeler_sims[1].creation_date = ANON_BEFORE - datetime.timedelta(days=2)
    modeler_sims[1].save()
    assert set(Simulation.objects.public_sims()) == set(
        [modeler_sims[0]] + modeler_sims[2:]
    )


class TestCollaborators:
    """
    Test plan restrictions regarding making sims private and adding
    collaborators to private sims.

    Related: webapp/apps/users/tests/test_models.py::TestCollaborators
    """

    def test_free_tier(self, db, get_inputs, meta_param_dict, free_profile):
        """
        Test private sim can not have any collaborators but
        public is unlimited.
        """
        sims = []
        for i in range(FREE_PRIVATE_SIMS):
            inputs = _submit_inputs(
                "Used-for-testing", get_inputs, meta_param_dict, free_profile
            )

            _, submit_sim = _submit_sim(inputs)
            sim = submit_sim.submit()
            sim.status = "SUCCESS"
            sim.save()
            sims.append(sim)

        for sim in sims[:-1]:
            sim.make_private_test()
            sim.is_public = False
            sim.save()

        # Error on making sim private in free tier.
        with pytest.raises(PrivateSimException) as excinfo:
            sim.make_private_test()

        assert excinfo.value.todict() == {
            "upgrade_to": "pro",
            "resource": PrivateSimException.resource,
            "test_name": "make_simulation_private",
            "msg": PrivateSimException.msg,
        }

        # test no limit on collaborators when sim is public.
        sim.is_public = True
        sim.save()

        for collab in gen_collabs(3):
            sim.assign_role("read", collab.user)
            assert (
                get_perms(collab.user, sim) == ["read_simulation"]
                and sim.role(collab.user) == "read"
            )

        with pytest.raises(CollaboratorLimitException):
            sim.make_private_test()

    def test_pro_tier(self, db, get_inputs, meta_param_dict, pro_profile, profile):
        """
        Test able to add more than one collaborator with a private
        and public sim.
        """
        inputs = _submit_inputs(
            "Used-for-testing", get_inputs, meta_param_dict, pro_profile
        )

        _, submit_sim = _submit_sim(inputs)
        sim = submit_sim.submit()
        sim.status = "SUCCESS"
        sim.save()

        collabs = list(gen_collabs(3))

        for collab in collabs:
            sim.assign_role("read", collab.user)
            assert (
                get_perms(collab.user, sim) == ["read_simulation"]
                and sim.role(collab.user) == "read"
            )

        # OK making sim private.
        sim.make_private_test()

        sim.is_public = True
        sim.save()

        for collab in collabs:
            sim.assign_role(None, collab.user)
            assert sim.role(collab.user) == None

        for collab in collabs:
            sim.assign_role("read", collab.user)
            assert (
                get_perms(collab.user, sim) == ["read_simulation"]
                and sim.role(collab.user) == "read"
            )

        # OK making sim private.
        sim.make_private_test()
