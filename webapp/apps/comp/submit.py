import datetime
from collections import namedtuple

from django.utils import timezone
from django import forms
from django.utils.safestring import mark_safe
from django.http import HttpResponse, HttpRequest
from rest_framework import status
from rest_framework.response import Response

from webapp.apps.users.models import Project
from webapp.apps.comp import actions
from webapp.apps.comp.compute import Compute
from webapp.apps.comp.exceptions import ValidationError
from webapp.apps.comp.forms import InputsForm
from webapp.apps.comp.ioutils import IOClasses
from webapp.apps.comp.models import Inputs, Simulation
from webapp.apps.comp.parser import Parser
from webapp.apps.comp.serializers import InputsSerializer
from webapp.apps.comp.forms import InputsForm
from webapp.apps.comp.constants import OUT_OF_RANGE_ERROR_MSG, WEBAPP_VERSION

BadPost = namedtuple("BadPost", ["http_response", "has_errors"])
PostResult = namedtuple("PostResult", ["submit", "save"])


class Submit:

    webapp_version = WEBAPP_VERSION

    def __init__(
        self,
        request: HttpRequest,
        project: Project,
        ioutils: IOClasses,
        compute: Compute,
    ):
        self.request = request
        self.project = project
        self.meta_parameters = ioutils.displayer.parsed_meta_parameters()
        self.ioutils = ioutils
        self.compute = compute
        self.model = None
        self.badpost = None
        self.valid_meta_params = {}

        self.get_fields()
        self.create_model()
        if self.badpost is not None:
            return
        if self.stop_submission:
            self.handle_errors()
        else:
            self.submit()

    def get_fields(self):
        fields = self.request.POST.dict()
        fields.pop("full_calc", None)
        self.has_errors = forms.BooleanField(required=False).clean(fields["has_errors"])
        self.fields = fields
        self.valid_meta_params = self.meta_parameters.validate(self.fields)

    def create_model(self):
        self.form = InputsForm(
            self.project,
            self.ioutils.displayer,
            dict(self.fields, **self.valid_meta_params),
        )
        if self.form.non_field_errors():
            self.badpost = BadPost(
                http_response=HttpResponse("Bad Input!", status=400), has_errors=True
            )
            return

        self.is_valid = self.form.is_valid()
        if self.is_valid:
            self.model = self.form.save(commit=False)
            parser = self.ioutils.Parser(
                self.project,
                self.ioutils.displayer,
                self.model.gui_inputs,
                **self.valid_meta_params,
            )

            errors_warnings, adjustment, inputs_file = parser.parse_parameters()
            self.model.adjustment = adjustment
            self.model.meta_parameters = self.valid_meta_params
            self.model.inputs_file = inputs_file
            self.model.errors_warnings = errors_warnings
            self.model.save()

    @property
    def stop_submission(self):
        if getattr(self, "_stop_submission", None) is not None:
            return self._stop_submission
        if self.model is not None:
            self.warn_msgs = any(
                len(self.model.errors_warnings[inputs_style]["warnings"]) > 0
                for inputs_style in self.model.errors_warnings
            )
            self.error_msgs = any(
                len(self.model.errors_warnings[inputs_style]["errors"]) > 0
                for inputs_style in self.model.errors_warnings
            )
        else:
            self.warn_msgs, self.error_msgs = None, None
        stop_errors = not self.is_valid or self.error_msgs
        self._stop_submission = stop_errors or (not self.has_errors and self.warn_msgs)
        return self._stop_submission

    def handle_errors(self):
        if self.warn_msgs or self.error_msgs or self.form.errors:
            self.form.add_error(None, OUT_OF_RANGE_ERROR_MSG)
        _, defaults = self.ioutils.displayer.package_defaults()

        def add_errors(param, msgs, _defaults):
            if _defaults:
                param_data = _defaults.get(param, None)
                if param_data:
                    title = param_data["title"]
                else:
                    title = param
            else:
                title = param
            msg_html = "".join([f"<li>{msg}</li>" for msg in msgs])
            message = mark_safe(f"<p>{title}:</p><ul>{msg_html}</ul>")
            self.form.add_error(None, message)

        if self.warn_msgs or self.error_msgs:
            for inputs_style in self.model.errors_warnings:
                self.ioutils.Parser.append_errors_warnings(
                    self.model.errors_warnings[inputs_style],
                    add_errors,
                    {} if inputs_style == "GUI" else defaults[inputs_style],
                )

    def submit(self):
        data = {
            "meta_param_dict": self.valid_meta_params,
            "adjustment": self.model.deserialized_inputs,
        }
        print("submit", data)
        self.submitted_id, self.max_q_length = self.compute.submit_job(
            data, self.project.worker_ext(action=actions.SIM)
        )


class APISubmit(Submit):
    def get_fields(self):
        self.has_errors = False

    def create_model(self):
        self.ser = InputsSerializer(data=self.request.data)
        self.is_valid = self.ser.is_valid()
        if self.is_valid:
            validated_data = self.ser.validated_data
            meta_parameters = validated_data.get("meta_parameters", {})
            adjustment = validated_data.get("adjustment", {})
            try:
                self.valid_meta_params = self.meta_parameters.validate(meta_parameters)
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

            errors_warnings, adjustment, inputs_file = parser.parse_parameters()
            self.model = self.ser.save(
                meta_parameters=self.valid_meta_params,
                adjustment=adjustment,
                errors_warnings=errors_warnings,
                inputs_file=inputs_file,
                project=self.project,
            )

        else:
            self.badpost = BadPost(
                http_response=Response(
                    self.ser.errors, status=status.HTTP_400_BAD_REQUEST
                ),
                has_errors=True,
            )

    def handle_errors(self):
        """Nothing to do for REST API"""
        pass


class Save:
    def __init__(self, submit, runmodel=None):
        """
        Retrieve model run data from instance of `Submit`. Save to `RunModel`
        instance. Return that instance.

        Returns:
        --------
        Simulation
        """
        # create OutputUrl object
        if runmodel is None:
            runmodel = Simulation()
        runmodel.status = "PENDING"
        runmodel.job_id = submit.submitted_id
        runmodel.inputs = submit.model
        runmodel.owner = getattr(submit.request.user, "profile", None)
        runmodel.project = submit.project
        runmodel.sponsor = runmodel.project.sponsor
        # TODO: collect upstream version
        runmodel.model_vers = None
        runmodel.webapp_vers = submit.webapp_version
        runmodel.model_pk = Simulation.objects.next_model_pk(runmodel.project)

        cur_dt = timezone.now()
        future_offset_seconds = (submit.max_q_length) * runmodel.project.exp_task_time
        future_offset = datetime.timedelta(seconds=future_offset_seconds)
        expected_completion = cur_dt + future_offset
        runmodel.exp_comp_datetime = expected_completion
        runmodel.save()
        self.runmodel_instance = runmodel


def handle_submission(
    request: HttpRequest,
    project: Project,
    ioutils: IOClasses,
    compute: Compute,
    submit_class: Submit = Submit,
):
    sub = submit_class(request, project, ioutils, compute)
    if sub.badpost is not None:
        return sub.badpost
    elif sub.stop_submission:
        return PostResult(sub, None)
    else:
        save = Save(sub)
        return PostResult(sub, save)
