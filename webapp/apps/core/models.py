import datetime
import uuid

from dataclasses import dataclass, field
from typing import List, Union

from django.db import models
from django.utils.functional import cached_property
from django.contrib.postgres.fields import JSONField
from django.utils.timezone import make_aware

from webapp.apps.users.models import Project, Profile


class CoreInputs(models.Model):
    raw_gui_inputs = JSONField(default=None, blank=True, null=True)
    gui_inputs = JSONField(default=None, blank=True, null=True)

    # Validated GUI input that has been parsed to have the correct data types,
    # or JSON reform uploaded as file
    inputs_file = JSONField(default=dict, blank=True, null=True)

    errors_warnings_text = JSONField(default=None, blank=True, null=True)

    # The parameters that will be used to run the model
    upstream_parameters = JSONField(default=dict, blank=True, null=True)

    @property
    def deserialized_inputs(self):
        """
        Method for de-serializing parameters for submission to the modeling
        project. This is helpful if information required for deserializing an
        object is lost during serialization. For example, projects that depend
        on integer keys in a dictionary will run into issues with those keys
        being converted into strings during serialization.
        """
        return self.upstream_parameters

    class Meta:
        abstract = True
        # permissions = (('run_model', 'Can run model'),)


class CoreRun(models.Model):
    dimension_name = "Dimension"

    # Subclasses must implement:
    # inputs = models.OneToOneField(CoreInputs)
    meta_data = JSONField(default=None, blank=True, null=True)
    outputs = JSONField(default=None, blank=True, null=True)
    aggr_outputs = JSONField(default=None, blank=True, null=True)
    error_text = models.CharField(null=True, blank=True, default=None, max_length=4000)
    profile = models.ForeignKey(
        Profile,
        on_delete=models.PROTECT,
        null=True,
        related_name="%(app_label)s_%(class)s_runs",
    )
    sponsor = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(app_label)s_%(class)s_sponsored_runs",
    )
    project = models.ForeignKey(
        Project, on_delete=models.PROTECT, related_name="%(app_label)s_%(class)s_runs"
    )
    # run-time in seconds
    run_time = models.IntegerField(default=0)
    # run cost can be very small. ex: 4 sec * ($0.09/hr)/3600
    run_cost = models.DecimalField(max_digits=9, decimal_places=4, default=0.0)
    creation_date = models.DateTimeField(
        default=make_aware(datetime.datetime(2015, 1, 1))
    )
    exp_comp_datetime = models.DateTimeField(
        default=make_aware(datetime.datetime(2015, 1, 1))
    )
    job_id = models.UUIDField(blank=True, default=None, null=True)
    upstream_vers = models.CharField(blank=True, default=None, null=True, max_length=50)
    webapp_vers = models.CharField(blank=True, default=None, null=True, max_length=50)

    def get_absolute_url(self):
        raise NotImplementedError()

    def get_absolute_edit_url(self):
        raise NotImplementedError()

    def get_absolute_download_url(self):
        raise NotImplementedError()

    def zip_filename(self):
        return "comp.zip"

    @cached_property
    def dimension(self):
        # return unique values set at the dimension level.
        return list({item["dimension"] for item in self.outputs if item["dimension"]})

    @property
    def effective_cost(self):
        return self.project.run_cost(self.run_time, adjust=True)

    class Meta:
        abstract = True


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
