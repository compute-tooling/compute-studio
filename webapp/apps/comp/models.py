import datetime
import uuid
import json
import pytz
import os

from dataclasses import dataclass, field
from typing import List, Union

from django.db import models
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.utils import timezone
from django.contrib.postgres.fields import JSONField as JSONBField
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import PermissionDenied

from guardian.shortcuts import assign_perm, remove_perm, get_perms, get_users_with_perms

import cs_storage

from webapp.settings import HAS_USAGE_RESTRICTIONS, USE_STRIPE

from webapp.apps.comp import utils
from webapp.apps.comp.exceptions import (
    ForkObjectException,
    PermissionExpiredException,
    ResourceLimitException,
    VersionMismatchException,
)


# 11:59 on night of deployment
ANON_BEFORE = datetime.datetime(
    2020, 1, 16, 23, 59, 59, tzinfo=pytz.timezone("US/Eastern")
)


class JSONField(JSONBField):
    def db_type(self, connection):
        return "json"


class ModelConfigManager(models.Manager):
    def get(self, project, model_version, meta_parameters_values, **kwargs):
        if meta_parameters_values:
            mp_search_kwargs = {
                f"meta_parameters_values__{name}": val
                for name, val in meta_parameters_values.items()
            }
        else:
            mp_search_kwargs = {"meta_parameters_values": {}}
        kwargs.update(mp_search_kwargs)
        return super().get(model_version=model_version, project=project, **kwargs)


class ModelConfig(models.Model):
    project = models.ForeignKey(
        "users.Project",
        on_delete=models.SET_NULL,
        related_name="model_configs",
        null=True,
    )
    inputs_version = models.CharField(choices=(("v1", "Version 1"),), max_length=10)
    model_version = models.CharField(
        blank=True, default=None, null=True, max_length=100
    )
    creation_date = models.DateTimeField(default=timezone.now)

    meta_parameters_values = JSONBField(null=True)
    meta_parameters = JSONField(default=dict)
    model_parameters = JSONField(default=dict)

    objects = ModelConfigManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "model_version", "meta_parameters_values"],
                name="unique_model_config",
            )
        ]


class Inputs(models.Model):
    parent_sim = models.ForeignKey(
        "Simulation", null=True, related_name="child_inputs", on_delete=models.SET_NULL
    )
    model_config = models.ForeignKey(
        ModelConfig,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inputs_instances",
    )
    meta_parameters = JSONBField(default=None, blank=True, null=True)
    raw_gui_inputs = JSONBField(default=None, blank=True, null=True)
    gui_inputs = JSONBField(default=None, blank=True, null=True)

    # Validated GUI input that has been parsed to have the correct data types,
    # or JSON reform uploaded as file
    custom_adjustment = JSONBField(default=dict, blank=True, null=True)

    errors_warnings = JSONBField(default=None, blank=True, null=True)

    # The parameters that will be used to run the model
    adjustment = JSONBField(default=dict, blank=True, null=True)

    # If project changes input type, we still want to know the type of the
    # previous model runs' inputs.
    inputs_style = models.CharField(
        choices=(("paramtools", "paramtools"), ("taxcalc", "taxcalc")), max_length=32
    )

    project = models.ForeignKey(
        "users.Project", on_delete=models.SET_NULL, related_name="sim_params", null=True
    )

    owner = models.ForeignKey(
        "users.Profile", on_delete=models.CASCADE, null=True, related_name="inputs"
    )
    traceback = models.CharField(null=True, blank=True, default=None, max_length=8000)
    job_id = models.UUIDField(blank=True, default=None, null=True)
    status = models.CharField(
        choices=(
            ("STARTED", "Started"),
            ("PENDING", "Pending"),
            ("SUCCESS", "Success"),
            ("INVALID", "Invalid"),
            ("FAIL", "Fail"),
            ("WORKER_FAILURE", "Worker Failure"),
        ),
        max_length=20,
    )

    client = models.CharField(
        choices=(
            ("web-alpha", "Web-Alpha"),
            ("web-beta", "Web-Beta"),
            ("rest-api", "REST API"),
        ),
        max_length=32,
    )

    @property
    def deserialized_inputs(self):
        """
        Method for de-serializing parameters for submission to the modeling
        project. This is helpful if information required for deserializing an
        object is lost during serialization. For example, projects that depend
        on integer keys in a dictionary will run into issues with those keys
        being converted into strings during serialization.


        TODO: should be moved to a function corresponding to the inputs_style
        """
        if self.inputs_style == "taxcalc":
            return utils.json_int_key_encode(self.adjustment)
        else:
            return self.adjustment

    @property
    def display_params(self):
        return self.custom_adjustment or self.adjustment

    @property
    def pretty_meta_parameters(self):
        return json.dumps(self.meta_parameters, indent=4)

    def parent_model_pk(self):
        if self.parent_sim is not None:
            return self.parent_sim.model_pk
        else:
            return None

    def get_absolute_api_url(self):
        kwargs = {
            "model_pk": self.sim.model_pk,
            "title": self.project.title,
            "username": self.project.owner.user.username,
        }
        return reverse("detail_myinputs_api_model_pk", kwargs=kwargs)

    def get_absolute_url(self):
        kwargs = {
            "model_pk": self.sim.model_pk,
            "title": self.project.title,
            "username": self.project.owner.user.username,
        }
        return reverse("edit", kwargs=kwargs)

    def has_admin_access(self, user):
        return self.sim.has_admin_access(user)

    def has_write_access(self, user):
        return self.sim.has_write_access(user)

    def has_read_access(self, user):
        return self.sim.has_read_access(user)

    def role(self, user):
        return self.sim.role(user)


class SimulationManager(models.Manager):
    def get_object_from_screenshot(self, output_id, user, http_404_on_fail=False):
        queryset = self.filter(
            outputs__outputs__renderable__outputs__contains=[{"id": output_id}],
        )
        result = None
        for sim in queryset:
            if sim.has_read_access(user):
                result = sim
                break

        if result is None and len(queryset) == 0 and http_404_on_fail:
            raise Http404(f"Unable to find Simulation with id {output_id}.")
        elif result is None and len(queryset) == 0:
            raise Simulation.DoesNotExist(
                "Unable to find Simulation with id {output_id}."
            )
        elif result is None and len(queryset) > 0:
            raise PermissionDenied()
        else:
            return result

    def next_model_pk(self, project):
        curr_max = Simulation.objects.filter(project=project).aggregate(
            models.Max("model_pk")
        )["model_pk__max"]
        if curr_max == -1 or curr_max is None:
            return 1
        else:
            return curr_max + 1

    def new_sim(self, user, project, inputs_status=None):
        """
        Create a new simulation for the user and project. If multiple
        requests are made to the /new/ endpoint at once there may be
        a race condition where multiple simulations are created with
        the same model specific primary key (model_pk) causing an
        IntegrityError. The strategy for handling this is to check
        the Simulation with the model_pk that caused the IntegrityError:

        - Case 1: `user` is the owner of the other simulation. We assume
        that this was caused by a double click or similar and return
        the existing simulation with the same model_pk.

        - Case 2: Multiple new simulations were created at once. In this
        case we try to create a new simulation again.

        Methods submitting a batch of simulations at once, should set
        inputs_status="PENDING". This creates inputs objects that are
        PENDING by default and thus force new Simulation objects to be
        created on each request even if they arrive at the same time.
        """
        model_pk = None
        try:
            # transaction.atomic will roll back any changes
            # if there is an integrity error.
            with transaction.atomic():
                inputs = Inputs.objects.create(
                    owner=user.profile,
                    project=project,
                    status=inputs_status or "STARTED",
                    adjustment={},
                    meta_parameters={},
                    errors_warnings={},
                )
                model_pk = self.next_model_pk(project)
                sim = self.create(
                    owner=user.profile,
                    project=project,
                    model_pk=model_pk,
                    inputs=inputs,
                    status="STARTED",
                    is_public=False,
                )
                sim.authors.set([user.profile])
                sim.grant_admin_permissions(user)
                return sim
        except IntegrityError:
            # Case 1:
            if model_pk is not None:
                sim = Simulation.objects.get(project=project, model_pk=model_pk)
                if sim.owner.user == user and sim.inputs.status == "STARTED":
                    return sim
            # Case 2:
            return self.new_sim(user, project, inputs_status)

    def fork(self, sim, user):
        if sim.inputs.status == "PENDING":
            raise ForkObjectException(
                "Simulations may not be forked while they are in a pending state. "
                "Please try again once validation has completed."
            )
        if sim.status == "PENDING":
            raise ForkObjectException(
                "Simulations may not be forked while they are in a pending state. "
                "Please try again once the simulation has completed."
            )
        inputs = Inputs.objects.create(
            owner=user.profile,
            project=sim.project,
            status=sim.inputs.status,
            adjustment=sim.inputs.adjustment,
            meta_parameters=sim.inputs.meta_parameters,
            errors_warnings=sim.inputs.errors_warnings,
            custom_adjustment=sim.inputs.custom_adjustment,
            parent_sim=sim,
            traceback=sim.inputs.traceback,
            client=sim.inputs.client,
        )
        sim = self.create(
            owner=user.profile,
            title=sim.title,
            readme=sim.readme,
            last_modified=sim.last_modified,
            parent_sim=sim,
            inputs=inputs,
            meta_data=sim.meta_data,
            outputs=sim.outputs,
            traceback=sim.traceback,
            sponsor=sim.sponsor,
            project=sim.project,
            run_time=sim.run_time,
            run_cost=0,
            exp_comp_datetime=sim.exp_comp_datetime,
            model_version=sim.model_version,
            model_pk=self.next_model_pk(sim.project),
            is_public=False,
            status=sim.status,
        )
        sim.authors.set([user.profile])
        sim.grant_admin_permissions(user)
        return sim

    def public_sims(self):
        return self.filter(creation_date__gt=ANON_BEFORE, is_public=True)


class SimulationPermissions:
    READ = (
        "read_simulation",
        "Users with this permission may view this simulation, even if it's private.",
    )
    WRITE = (
        "write_simulation",
        "Users with this permission may edit the title, description, and simulation parameters.",
    )
    ADMIN = (
        "admin_simulation",
        "Users with this permission control the visibility of this simulation and who has read, write, and admin access to it.",
    )


class Simulation(models.Model):
    READ = SimulationPermissions.READ
    WRITE = SimulationPermissions.WRITE
    ADMIN = SimulationPermissions.ADMIN

    # TODO: dimension needs to go
    dimension_name = "Dimension--needs to go"
    title = models.CharField(default="Untitled Simulation", max_length=500)
    readme = JSONBField(null=True, default=None, blank=True)
    last_modified = models.DateTimeField(default=timezone.now)
    parent_sim = models.ForeignKey(
        "self", null=True, related_name="child_sims", on_delete=models.SET_NULL
    )
    inputs = models.OneToOneField(Inputs, on_delete=models.CASCADE, related_name="sim")
    meta_data = JSONBField(default=None, blank=True, null=True)
    outputs = JSONBField(default=None, blank=True, null=True)
    aggr_outputs = JSONBField(default=None, blank=True, null=True)
    traceback = models.CharField(null=True, blank=True, default=None, max_length=8000)
    owner = models.ForeignKey(
        "users.Profile", on_delete=models.CASCADE, null=True, related_name="sims"
    )
    authors = models.ManyToManyField("users.Profile", related_name="authored_sims")
    sponsor = models.ForeignKey(
        "users.Profile",
        on_delete=models.SET_NULL,
        null=True,
        related_name="sponsored_sims",
    )
    project = models.ForeignKey(
        "users.Project", on_delete=models.SET_NULL, related_name="sims", null=True
    )
    notify_on_completion = models.BooleanField(default=False)
    # run-time in seconds
    run_time = models.IntegerField(default=0)
    # run cost can be very small. ex: 4 sec * ($0.09/hr)/3600
    run_cost = models.DecimalField(max_digits=9, decimal_places=4, default=0.0)
    creation_date = models.DateTimeField(default=timezone.now)
    exp_comp_datetime = models.DateTimeField(default=timezone.now)
    job_id = models.UUIDField(blank=True, default=None, null=True)
    model_version = models.CharField(blank=True, default=None, null=True, max_length=50)
    webapp_vers = models.CharField(blank=True, default=None, null=True, max_length=50)
    model_pk = models.IntegerField()

    is_public = models.BooleanField(default=True)

    status = models.CharField(
        choices=(
            ("STARTED", "Started"),
            ("PENDING", "Pending"),
            ("SUCCESS", "Success"),
            ("FAIL", "Fail"),
            ("WORKER_FAILURE", "Worker Failure"),
        ),
        max_length=20,
    )

    objects = SimulationManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "model_pk"], name="unique_model_pk"
            )
        ]
        permissions = (
            SimulationPermissions.READ,
            SimulationPermissions.WRITE,
            SimulationPermissions.ADMIN,
        )

    def __str__(self):
        return f"{self.project}#{self.model_pk}"

    def get_absolute_url(self):
        kwargs = {
            "model_pk": self.model_pk,
            "title": self.project.title,
            "username": self.project.owner.user.username,
        }
        if self.outputs_version() == "v0":
            return self.get_absolute_v0_url()
        else:
            return reverse("outputs", kwargs=kwargs)

    def get_absolute_api_url(self):
        kwargs = {
            "model_pk": self.model_pk,
            "title": self.project.title,
            "username": self.project.owner.user.username,
        }
        return reverse("detail_api", kwargs=kwargs)

    def get_absolute_edit_url(self):
        kwargs = {
            "model_pk": self.model_pk,
            "title": self.project.title,
            "username": self.project.owner.user.username,
        }
        return reverse("edit", kwargs=kwargs)

    def get_absolute_download_url(self):
        kwargs = {
            "model_pk": self.model_pk,
            "title": self.project.title,
            "username": self.project.owner.user.username,
        }
        return reverse("download", kwargs=kwargs)

    def get_absolute_v0_url(self):
        kwargs = {
            "model_pk": self.model_pk,
            "title": self.project.title,
            "username": self.project.owner.user.username,
        }
        if self.outputs_version() == "v0":
            return reverse("v0_outputs", kwargs=kwargs)

        raise VersionMismatchException(
            f"{self} is version {self.outputs_version()} != v0."
        )

    def zip_filename(self):
        return f"{self.project.title}_{self.model_pk}.zip"

    def json_filename(self):
        return f"{self.project.title}_{self.model_pk}.json"

    def compute_eta(self, reference_time=None):
        if reference_time is None:
            reference_time = timezone.now()
        exp_comp_dt = self.exp_comp_datetime
        dt = exp_comp_dt - reference_time
        eta = dt.total_seconds()
        return eta if eta > 0 else 0

    def compute_original_eta(self):
        return self.compute_eta(self.creation_date)

    @cached_property
    def dimension(self):
        # return unique values set at the dimension level.
        return list(
            {item["dimension"] for item in self.outputs["outputs"] if item["dimension"]}
        )

    @property
    def effective_cost(self):
        return self.project.run_cost(self.run_time, adjust=True)

    def parent_sims(self, user=None):
        """
        Recursively walk back up to the original simulation. All public simulations
        are included, and private simulations are only included if the user is
        provided and has read access.
        """
        parent_sims = []
        sim = self
        while sim.parent_sim != None:
            if sim.parent_sim.is_public or sim.parent_sim.has_read_access(user):
                parent_sims.append(sim.parent_sim)
            sim = sim.parent_sim
        return parent_sims

    def is_owner(self, user):
        return user == self.owner.user

    def _collaborator_test(self, test_name, adding_collaborator=True):
        if not HAS_USAGE_RESTRICTIONS:
            return

        permission_objects = get_users_with_perms(self)

        # number of additional collaborators besides owner.
        num_collaborators = permission_objects.count() - 1

        if adding_collaborator:
            num_collaborators += 1

        user = self.owner.user
        customer = getattr(user, "customer", None)
        if customer is None:
            if num_collaborators > 0:
                raise ResourceLimitException(
                    "collaborators",
                    test_name,
                    "plus",
                    ResourceLimitException.collaborators_msg,
                )

        if customer is not None:
            current_plan = customer.current_plan()

            if num_collaborators > 0 and current_plan["name"] == "free":
                raise ResourceLimitException(
                    "collaborators",
                    test_name,
                    "plus",
                    ResourceLimitException.collaborators_msg,
                )

            if num_collaborators > 1 and current_plan["name"] == "plus":
                raise ResourceLimitException(
                    "collaborators",
                    test_name,
                    "pro",
                    ResourceLimitException.collaborators_msg,
                )

    def add_collaborator_test(self):
        """
        Test if user's plan allows them to add more collaborators
        to this simulation.
        """
        if self.is_public:
            return
        return self._collaborator_test("add_collaborator", adding_collaborator=True)

    def make_private_test(self):
        """
        Test if user's plan allows them to make the simulation private with
        the existing number of collaborators.
        """
        return self._collaborator_test("make_private", adding_collaborator=False)

    """
    The methods below are used for checking if a user has read, write, or admin
    access to a specific simulation. Users can only have one of these permissions
    at a time, but users with a higher level permission inherit the read/write
    access from the lower level permissions, too.
    """

    def has_admin_access(self, user):
        if not user or not user.is_authenticated:
            return False

        return user.has_perm(Simulation.ADMIN[0], self)

    def has_write_access(self, user):
        """
        Currently, this is just an alias for is_owner.
        """
        if not user or not user.is_authenticated:
            return False

        return user.has_perm(Simulation.WRITE[0], self) or self.has_admin_access(user)

    def has_read_access(self, user):
        # Everyone has access to this sim.
        if self.is_public:
            return True

        if not user or not user.is_authenticated:
            return False
        return user.has_perm(Simulation.READ[0], self) or self.has_write_access(user)

    def remove_permissions(self, user):
        for permission in get_perms(user, self):
            remove_perm(permission, user, self)

    def grant_admin_permissions(self, user):
        self.remove_permissions(user)
        self.add_collaborator_test()
        assign_perm(Simulation.ADMIN[0], user, self)

    def grant_write_permissions(self, user):
        self.remove_permissions(user)
        self.add_collaborator_test()
        assign_perm(Simulation.WRITE[0], user, self)

    def grant_read_permissions(self, user):
        self.remove_permissions(user)
        self.add_collaborator_test()
        assign_perm(Simulation.READ[0], user, self)

    @transaction.atomic
    def assign_role(self, role, user):
        """
        Wrapper for granting and revoking permissions for a user.
        Each of the methods below complete multiple DB transactions
        which can cause some race condition-related bugs.

        Roles: read, write, admin, None (none removes all perms.)
        """
        if role == None:
            self.remove_permissions(user)
        elif role == "read":
            self.grant_read_permissions(user)
        elif role == "write":
            self.grant_write_permissions(user)
        elif role == "admin":
            self.grant_admin_permissions(user)
        else:
            raise ValueError(
                f"Received invalid role: {role}. Choices are read, write, or admin."
            )

    def role(self, user):
        if not user or not user.is_authenticated:
            return None

        perms = get_perms(user, self)
        if not perms:
            return None
        elif perms == [Simulation.READ[0]]:
            return "read"
        elif perms == [Simulation.WRITE[0]]:
            return "write"
        elif perms == [Simulation.ADMIN[0]]:
            return "admin"

    def outputs_version(self):
        if self.outputs:
            return self.outputs["version"]
        else:
            return None

    def get_owner(self):
        """
        Return owner or "unsigned" depending on whether the simulation
        was created before the ANON_BEFORE cutoff date. This should
        be used instead of 'owner' on serializer classes for
        Simulation.

        This ensures that simulations created under the assumption that
        they are unsigned remain unsigned.
        """
        if self.creation_date < ANON_BEFORE:
            return "unsigned"
        else:
            return self.owner

    def get_authors(self):
        """
        This protects the identity of users who created simulations
        before ANON_BEFORE. See get_owner for more information.
        """
        if self.creation_date < ANON_BEFORE:
            return ["unsigned"]
        else:
            return self.authors

    def context(self, request=None):
        url = self.get_absolute_url()
        if request is not None:
            url = f"https://{request.get_host()}{url}"
        pic = None
        if self.outputs and self.outputs_version() != "v0":
            output = self.outputs["outputs"]["renderable"]["outputs"][:1]
            if output:
                pic = f"https://{request.get_host()}/data/{output[0]['id']}.png"

        return {"owner": self.get_owner(), "title": self.title, "url": url, "pic": pic}


def two_days_from_now():
    return timezone.now() + datetime.timedelta(days=2)


class PendingPermissionManger(models.Manager):
    def get_or_create(self, sim=None, profile=None, permission_name=None, **kwargs):
        pp, created = super().get_or_create(
            sim=sim, profile=profile, permission_name=permission_name, **kwargs
        )
        # guarantee use at least as the read role.
        if pp.sim.role(pp.profile.user) is None:
            pp.sim.assign_role("read", pp.profile.user)
        return pp, created


class PendingPermission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sim = models.ForeignKey(
        Simulation, on_delete=models.CASCADE, related_name="pending_permissions"
    )
    profile = models.ForeignKey(
        "users.Profile", on_delete=models.CASCADE, related_name="pending_permissions"
    )
    permission_name = models.CharField(
        choices=(("add_author", "Permission to add author."),), max_length=32
    )
    creation_date = models.DateTimeField(default=timezone.now)

    expiration_date = models.DateTimeField(default=two_days_from_now)

    objects = PendingPermissionManger()

    def add_author(self):
        if self.is_expired():
            raise PermissionExpiredException()
        self.sim.authors.add(self.profile)
        self.delete()

    def is_expired(self):
        return timezone.now() > self.expiration_date

    def get_absolute_url(self):
        kwargs = {
            "id": self.id,
            "model_pk": self.sim.model_pk,
            "title": self.sim.project.title,
            "username": self.sim.project.owner.user.username,
        }
        return reverse("permissions_pending", kwargs=kwargs)

    def get_absolute_grant_url(self):
        kwargs = {
            "id": self.id,
            "model_pk": self.sim.model_pk,
            "title": self.sim.project.title,
            "username": self.sim.project.owner.user.username,
        }
        return reverse("permissions_grant", kwargs=kwargs)


@dataclass
class Tag:
    key: str
    values: List["TagOption"]
    hidden: bool = True


@dataclass
class TagOption:
    value: str
    title: str
    tooltip: Union[str, None] = None
    active: bool = False
    children: List[Tag] = field(default_factory=list)
