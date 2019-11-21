import datetime
import uuid
import json

from dataclasses import dataclass, field
from typing import List, Union
from hashids import Hashids

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.utils import timezone
from django.contrib.postgres.fields import JSONField
from django.utils.timezone import make_aware
from django.urls import reverse
from django.utils import timezone

from webapp.apps.comp import utils
from webapp.settings import INPUTS_SALT


hashids = Hashids(INPUTS_SALT, min_length=6)


class InputsQuerySet(models.QuerySet):
    def from_hashid(self, hashid):
        """
        Get inputs object from a hash of its pk. Return None
        if the decode does not resolve to a pk.
        """
        pk = hashids.decode(hashid)
        if not pk:
            return None
        else:
            return self.get(pk=pk[0])

    def get_object_from_hashid_or_404(self, hashid):
        """
        Get inputs object from a hash of its pk and
        raise 404 exception if it does not exist.
        """
        try:
            obj = self.from_hashid(hashid)
        except ObjectDoesNotExist:
            raise Http404("Object matching query does not exist")
        if obj:
            return obj
        else:
            raise Http404("Object matching query does not exist")


class Inputs(models.Model):
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

    objects = InputsQuerySet.as_manager()

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

    def get_absolute_api_url(self):
        kwargs = {
            "hashid": self.get_hashid(),
            "title": self.project.title,
            "username": self.project.owner.user.username,
        }
        return reverse("detail_myinputs_api", kwargs=kwargs)

    def get_edit_url(self):
        kwargs = {
            "hashid": self.get_hashid(),
            "title": self.project.title,
            "username": self.project.owner.user.username,
        }
        return reverse("edit_inputs", kwargs=kwargs)

    def get_hashid(self):
        return hashids.encode(self.pk)


class SimulationManager(models.Manager):
    def next_model_pk(self, project):
        curr_max = Simulation.objects.filter(project=project).aggregate(
            models.Max("model_pk")
        )["model_pk__max"]
        if curr_max == -1 or curr_max is None:
            return 1
        else:
            return curr_max + 1


class Simulation(models.Model):
    # TODO: dimension needs to go
    dimension_name = "Dimension--needs to go"

    inputs = models.OneToOneField(
        Inputs, on_delete=models.CASCADE, related_name="outputs"
    )
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

    status = models.CharField(
        choices=(
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
