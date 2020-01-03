import datetime
import uuid
import json

from dataclasses import dataclass, field
from typing import List, Union

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.utils import timezone
from django.contrib.postgres.fields import JSONField
from django.contrib.auth.models import Group
from django.utils.timezone import make_aware
from django.urls import reverse
from django.utils import timezone

from webapp.apps.comp import utils
from webapp.settings import INPUTS_SALT


class ForkObjectException(Exception):
    pass

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
        return user.is_authenticated and user == self.owner.user

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

    def new_sim(self, user, project):
        inputs = Inputs.objects.create(
            owner=user.profile,
            project=project,
            status="STARTED",
            adjustment={},
            meta_parameters={},
            errors_warnings={},
        )
        return self.create(
            owner=user.profile,
            project=project,
            model_pk=self.next_model_pk(project),
            inputs=inputs,
            status="STARTED",
            is_public=False,
        )

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
        return self.create(
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
            creation_date=sim.creation_date,
            exp_comp_datetime=sim.exp_comp_datetime,
            model_version=sim.model_version,
            model_pk=self.next_model_pk(sim.project),
            is_public=False,
            status=sim.status,
        )

class Simulation(models.Model):

    # TODO: dimension needs to go
    dimension_name = "Dimension--needs to go"
    title = models.CharField(default="Untitled Simulation", max_length=500)
    readme = models.CharField(null=True, default=None, blank=True, max_length=10000)
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
    sponsor = models.ForeignKey(
        "users.Profile",
        on_delete=models.SET_NULL,
        null=True,
        related_name="sponsored_sims",
    )
    project = models.ForeignKey(
        "users.Project", on_delete=models.SET_NULL, related_name="sims", null=True
    )
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

    def get_absolute_url(self):
        kwargs = {
            "model_pk": self.model_pk,
            "title": self.project.title,
            "username": self.project.owner.user.username,
        }
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

    def __str__(self):
        return (
            f"{self.project.owner.user.username}/{self.project.title}/{self.model_pk}"
        )

    def parent_sims(self):
        """Recursively walk back up to the original simulation"""
        parent_sims = []
        sim = self
        while sim.parent_sim != None:
            parent_sims.append(sim.parent_sim)
            sim = sim.parent_sim
        return parent_sims

    def has_write_access(self, user):
        return user.is_authenticated and user == self.owner.user

    def has_read_access(self, user):
        return self.is_public or (user.is_authenticated and user == self.owner.user)


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
