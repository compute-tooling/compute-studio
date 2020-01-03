import datetime
from collections import namedtuple

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpRequest
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response

from webapp.apps.users.models import Project

from webapp.apps.comp import actions
from webapp.apps.comp.constants import OUT_OF_RANGE_ERROR_MSG, WEBAPP_VERSION
from webapp.apps.comp.compute import Compute
from webapp.apps.comp.exceptions import ValidationError, BadPostException
from webapp.apps.comp.ioutils import IOClasses
from webapp.apps.comp.models import Inputs, Simulation
from webapp.apps.comp.serializers import InputsSerializer


User = get_user_model()


class SubmitInputs:

    webapp_version = WEBAPP_VERSION

    def __init__(
        self,
        request: HttpRequest,
        project: Project,
        ioutils: IOClasses,
        compute: Compute,
        sim: Simulation,
    ):
        self.request = request
        self.user = self.request.user
        self.project = project
        self.ioutils = ioutils
        self.compute = compute
        self.badpost = None
        self.meta_parameters = ioutils.displayer.parsed_meta_parameters()
        self.sim = sim

    def submit(self, save_only: bool = False):
        print(self.request.data)
        self.ser = InputsSerializer(instance=self.sim.inputs, data=self.request.data)
        is_valid = self.ser.is_valid()
        if not is_valid:
            raise BadPostException(self.ser.errors)

        validated_data = self.ser.validated_data
        meta_parameters = validated_data.get("meta_parameters", {})
        adjustment = validated_data.get("adjustment", {})
        parent_model_pk = validated_data.pop("parent_model_pk", None)

        if parent_model_pk is not None and self.sim.parent_sim is None:
            parent_sim = get_object_or_404(
                Simulation, project=self.project, model_pk=parent_model_pk
            )
        else:
            parent_sim = None

        try:
            self.valid_meta_params = self.meta_parameters.validate(meta_parameters)
            errors = None
        except ValidationError as ve:
            errors = str(ve)

        if errors:
            raise BadPostException(errors)

        parser = self.ioutils.Parser(
            self.project,
            self.ioutils.displayer,
            adjustment,
            compute=self.compute,
            **self.valid_meta_params,
        )

        result = parser.parse_parameters(save_only=save_only)
        self.inputs = self.ser.save(
            meta_parameters=self.valid_meta_params,
            adjustment=result["adjustment"],
            errors_warnings=result["errors_warnings"],
            custom_adjustment=result["custom_adjustment"],
            job_id=result.get("job_id", None),
            status="STARTED" if save_only else "PENDING",
            parent_sim=self.sim.parent_sim or parent_sim,
        )
        # case where parent sim exists and has not yet been assigned
        if not self.sim.parent_sim and parent_sim:
            self.sim.parent_sim = parent_sim
            self.sim.title = parent_sim.title
            self.sim.save()
        # TODO: remove assertion in productin code.
        assert self.inputs.sim == self.sim
        return self.inputs


class SubmitSim:
    def __init__(self, sim: Simulation, compute: Compute):
        self.compute = compute
        self.sim = sim

    def submit(self):
        inputs = self.sim.inputs
        data = {
            "meta_param_dict": inputs.meta_parameters,
            "adjustment": inputs.deserialized_inputs,
        }
        print("submit", data)
        self.submitted_id, self.max_q_length = self.compute.submit_job(
            data, inputs.project.worker_ext(action=actions.SIM)
        )
        print(f"job id: {self.submitted_id}")
        print(f"q lenghth: {self.max_q_length}")

        self.sim = self.save()
        return self.sim

    def save(self):
        sim = self.sim
        sim.status = "PENDING"
        sim.job_id = self.submitted_id
        sim.sponsor = sim.project.sponsor

        cur_dt = timezone.now()

        future_offset_seconds = (self.max_q_length) * sim.project.exp_task_time
        future_offset = datetime.timedelta(seconds=future_offset_seconds)
        expected_completion = cur_dt + future_offset
        sim.exp_comp_datetime = expected_completion

        sim.creation_date = cur_dt
        sim.save()
        return sim
