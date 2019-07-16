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
from webapp.apps.comp.exceptions import ValidationError
from webapp.apps.comp.ioutils import IOClasses
from webapp.apps.comp.models import Inputs, Simulation
from webapp.apps.comp.serializers import InputsSerializer

BadPost = namedtuple("BadPost", ["http_response", "has_errors"])
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

    def submit(self):
        print(self.request.data)
        self.ser = InputsSerializer(data=self.request.data)
        self.is_valid = self.ser.is_valid()
        if self.is_valid:
            validated_data = self.ser.validated_data
            meta_parameters = validated_data.get("meta_parameters", {})
            adjustment = validated_data.get("adjustment", {})
            try:
                self.valid_meta_params = meta_parameters.validate(meta_parameters)
                errors = None
            except ValidationError as ve:
                errors = str(ve)

            if errors:
                self.badpost = BadPost(
                    http_response=Response(errors, status=status.HTTP_400_BAD_REQUEST),
                    has_errors=True,
                )
                return

            parser = self.ioutils.Parser(
                self.project,
                self.ioutils.displayer,
                adjustment,
                **self.valid_meta_params,
            )

            result = parser.parse_parameters()
            self.model = self.ser.save(
                meta_parameters=self.valid_meta_params,
                adjustment=result["adjustment"],
                errors_warnings=result["errors_warnings"],
                inputs_file=result["inputs_file"],
                project=self.project,
                owner=getattr(self.request.user, "profile", None),
                job_id=result["job_id"],
            )
            return self.model
        else:
            self.badpost = BadPost(
                http_response=Response(
                    self.ser.errors, status=status.HTTP_400_BAD_REQUEST
                ),
                has_errors=True,
            )
            return self.badpost


class SubmitSim:
    def __init__(self, inputs: Inputs, compute: Compute, runmodel: Simulation = None):
        self.inputs = inputs
        self.compute = compute
        self.runmodel = runmodel

    def submit(self):
        data = {
            "meta_param_dict": self.valid_meta_params,
            "adjustment": self.model.deserialized_inputs,
        }
        print("submit", data)
        self.submitted_id, self.max_q_length = self.compute.submit_job(
            data, self.project.worker_ext(action=actions.SIM)
        )
        print(f"job id: {self.submitted_id}")
        print(f"q lenghth: {self.max_q_length}")

        self.save()
        return self.runmodel

    def save(self):
        # create OutputUrl object
        if self.runmodel is None:
            runmodel = Simulation()
        runmodel.status = "PENDING"
        runmodel.job_id = self.submitted_id
        runmodel.inputs = self.inputs
        runmodel.owner = self.inputs.owner
        runmodel.project = self.inputs.project
        runmodel.sponsor = runmodel.project.sponsor
        # TODO: collect upstream version
        runmodel.model_vers = None
        runmodel.webapp_vers = WEBAPP_VERSION
        runmodel.model_pk = Simulation.objects.next_model_pk(runmodel.project)

        cur_dt = timezone.now()
        future_offset_seconds = (self.max_q_length) * runmodel.project.exp_task_time
        future_offset = datetime.timedelta(seconds=future_offset_seconds)
        expected_completion = cur_dt + future_offset
        runmodel.exp_comp_datetime = expected_completion
        runmodel.save()
        self.runmodel = runmodel
