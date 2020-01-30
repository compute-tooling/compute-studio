import datetime
import uuid
import json
import pytz

from dataclasses import dataclass, field
from typing import List, Union

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.utils import timezone
from django.contrib.postgres.fields import JSONField
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

import cs_storage

from webapp.apps.comp import utils, exceptions
from webapp.settings import INPUTS_SALT


# 11:59 on night of deployment
ANON_BEFORE = datetime.datetime(
    2020, 1, 16, 23, 59, 59, tzinfo=pytz.timezone("US/Eastern")
)


class Inputs(models.Model):
    parent_sim = models.ForeignKey(
        "Simulation", null=True, related_name="child_inputs", on_delete=models.SET_NULL
    )
    meta_parameters = JSONField(default=None, blank=True, null=True)
    raw_gui_inputs = JSONField(default=None, blank=True, null=True)
    gui_inputs = JSONField(default=None, blank=True, null=True)

    # Validated GUI input that has been parsed to have the correct data types,
    # or JSON reform uploaded as file
    custom_adjustment = JSONField(default=dict, blank=True, null=True)

    errors_warnings = JSONField(default=None, blank=True, null=True)

    # The parameters that will be used to run the model
    adjustment = JSONField(default=dict, blank=True, null=True)

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

    def has_write_access(self, user):
        return self.sim.has_write_access(user)

    def has_read_access(self, user):
        return self.sim.has_read_access(user)


class SimulationManager(models.Manager):
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
            raise exceptions.ForkObjectException(
                "Simulations may not be forked while they are in a pending state. "
                "Please try again once validation has completed."
            )
        if sim.status == "PENDING":
            raise exceptions.ForkObjectException(
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
        return sim


class Simulation(models.Model):

    # TODO: dimension needs to go
    dimension_name = "Dimension--needs to go"
    title = models.CharField(default="Untitled Simulation", max_length=500)
    readme = JSONField(null=True, default=None, blank=True)
    last_modified = models.DateTimeField(default=timezone.now)
    parent_sim = models.ForeignKey(
        "self", null=True, related_name="child_sims", on_delete=models.SET_NULL
    )
    inputs = models.OneToOneField(Inputs, on_delete=models.CASCADE, related_name="sim")
    meta_data = JSONField(default=None, blank=True, null=True)
    outputs = JSONField(default=None, blank=True, null=True)
    aggr_outputs = JSONField(default=None, blank=True, null=True)
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

        raise exceptions.VersionMismatchException(
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

    def has_write_access(self, user):
        return bool(user and user.is_authenticated and user == self.owner.user)

    def has_read_access(self, user):
        return self.is_public or bool(
            user and user.is_authenticated and user == self.owner.user
        )

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
                output = cs_storage.add_screenshot_links(
                    {"renderable": {"outputs": output}}
                )
                pic = output["renderable"]["outputs"][0]["screenshot"]
        return {"owner": self.get_owner(), "title": self.title, "url": url, "pic": pic}


def two_days_from_now():
    return timezone.now() + datetime.timedelta(days=2)


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

    def add_author(self):
        if self.is_expired():
            raise exceptions.PermissionExpiredException()
        self.sim.authors.add(self.profile)
        self.delete()

    def is_expired(self):
        return timezone.now() > self.expiration_date

    def get_absolute_url(self):
        kwargs = {"id": self.id}
        return reverse("permissions_pending", kwargs=kwargs)

    def get_absolute_grant_url(self):
        kwargs = {"id": self.id}
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
