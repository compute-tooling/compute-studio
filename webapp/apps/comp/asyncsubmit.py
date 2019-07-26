import datetime
from collections import namedtuple

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpRequest
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
    ):
        self.request = request
        self.user = self.request.user
        self.project = project
        self.ioutils = ioutils
        self.compute = compute
        self.badpost = None
        self.meta_parameters = ioutils.displayer.parsed_meta_parameters()

    def submit(self):
        print(self.request.data)
        self.ser = InputsSerializer(data=self.request.data)
        is_valid = self.ser.is_valid()
        if not is_valid:
            raise BadPostException(self.ser.errors)

        validated_data = self.ser.validated_data
        meta_parameters = validated_data.get("meta_parameters", {})
        adjustment = validated_data.get("adjustment", {})
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
            extend=validated_data.get("extend", False) ** self.valid_meta_params,
        )

        result = parser.parse_parameters()
        self.inputs = self.ser.save(
            meta_parameters=self.valid_meta_params,
            adjustment=result["adjustment"],
            errors_warnings=result["errors_warnings"],
            inputs_file=result["inputs_file"],
            project=self.project,
            owner=getattr(self.request.user, "profile", None),
            job_id=result["job_id"],
            status="PENDING",
        )
        return self.inputs


class SubmitSim:
    def __init__(self, inputs: Inputs, compute: Compute, sim: Simulation = None):
        self.inputs = inputs
        self.compute = compute
        self.sim = sim

    def submit(self):
        data = {
            "meta_param_dict": self.inputs.meta_parameters,
            "adjustment": self.inputs.deserialized_inputs,
        }
        print("submit", data)
        self.submitted_id, self.max_q_length = self.compute.submit_job(
            data, self.inputs.project.worker_ext(action=actions.SIM)
        )
        print(f"job id: {self.submitted_id}")
        print(f"q lenghth: {self.max_q_length}")

        self.sim = self.save()
        return self.sim

    def save(self):
        # create OutputUrl object
        if self.sim is None:
            sim = Simulation()
        sim.status = "PENDING"
        sim.job_id = self.submitted_id
        sim.inputs = self.inputs
        sim.owner = self.inputs.owner
        sim.project = self.inputs.project
        sim.sponsor = sim.project.sponsor
        # TODO: collect upstream version
        sim.model_vers = None
        sim.webapp_vers = WEBAPP_VERSION
        sim.model_pk = Simulation.objects.next_model_pk(sim.project)

        cur_dt = timezone.now()
        future_offset_seconds = (self.max_q_length) * sim.project.exp_task_time
        future_offset = datetime.timedelta(seconds=future_offset_seconds)
        expected_completion = cur_dt + future_offset
        sim.exp_comp_datetime = expected_completion
        sim.save()
        return sim
