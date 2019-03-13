import datetime
from collections import namedtuple

from django.utils import timezone
from django import forms

from webapp.apps.users.models import Project
from webapp.apps.core import actions
from webapp.apps.core.parser import Parser
from webapp.apps.core.forms import InputsForm
from webapp.apps.core.constants import OUT_OF_RANGE_ERROR_MSG, WEBAPP_VERSION

BadPost = namedtuple("BadPost", ["http_response_404", "has_errors"])
PostResult = namedtuple("PostResult", ["submit", "save"])


class Submit:

    parser_class = Parser
    form_class = InputsForm
    webapp_version = WEBAPP_VERSION
    app_name = None
    upstream_version = None
    meta_parameters = None

    def __init__(self, request, compute):
        self.request = request
        self.compute = compute
        self.model = None
        self.badpost = None
        self.valid_meta_params = {}
        self.project = Project.objects.get(app_name=self.app_name)

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
        self.form = self.form_class(dict(self.fields, **self.valid_meta_params))
        if self.form.non_field_errors():
            self.badpost = BadPost(
                http_response_404=HttpResponse("Bad Input!", status=400),
                has_errors=True,
            )
            return

        self.is_valid = self.form.is_valid()
        if self.is_valid:
            self.model = self.form.save(commit=False)
            parser = self.parser_class(self.model.gui_inputs, **self.valid_meta_params)

            (
                upstream_parameters,
                upstream_json_files,
                errors_warnings,
            ) = parser.parse_parameters()
            self.model.upstream_parameters = upstream_parameters
            self.model.inputs_file = upstream_json_files
            self.model.errors_warnings = errors_warnings
            self.model.save()

    @property
    def stop_submission(self):
        if getattr(self, "_stop_submission", None) is not None:
            return self._stop_submission
        if self.model is not None:
            self.warn_msgs = any(
                len(self.model.errors_warnings[input_type]["warnings"]) > 0
                for input_type in self.model.errors_warnings
            )
            self.error_msgs = any(
                len(self.model.errors_warnings[input_type]["errors"]) > 0
                for input_type in self.model.errors_warnings
            )
        else:
            self.warn_msgs, self.error_msgs = None, None
        stop_errors = not self.is_valid or self.error_msgs
        self._stop_submission = stop_errors or (not self.has_errors and self.warn_msgs)
        return self._stop_submission

    def handle_errors(self):
        if self.warn_msgs or self.error_msgs or self.form.errors:
            self.form.add_error(None, OUT_OF_RANGE_ERROR_MSG)

        def add_errors(param, msg):
            message = "{param}: {msg}".format(param=param, msg=" ,".join(msg))
            self.form.add_error(None, message)

        if self.warn_msgs or self.error_msgs:
            for input_type in self.model.errors_warnings:
                self.parser_class.append_errors_warnings(
                    self.model.errors_warnings[input_type], add_errors
                )

    def submit(self):
        data = dict(
            {"user_mods": self.model.deserialized_inputs}, **self.valid_meta_params
        )
        print("submit", data)
        self.data_list = self.extend_data(data)
        print(self.data_list)
        url = self.project.worker_ext(action=actions.SIM)
        self.submitted_id, self.max_q_length = self.compute.submit_job(
            self.data_list, url
        )

    def extend_data(self, data):
        """Do nothing here."""
        return data


class Save:

    project_name = None
    runmodel = None

    def __init__(self, submit):
        """
        Retrieve model run data from instance of `Submit`. Save to `RunModel`
        instance. Return that instance.

        Returns:
        --------
        RunModel
        """
        # create OutputUrl object
        runmodel = self.runmodel()
        runmodel.job_id = submit.submitted_id
        runmodel.inputs = submit.model
        runmodel.profile = getattr(submit.request.user, "profile", None)
        runmodel.project = Project.objects.get(name=self.project_name)
        runmodel.sponsor = runmodel.project.sponsor
        runmodel.upstream_vers = submit.upstream_version
        runmodel.webapp_vers = submit.webapp_version

        cur_dt = timezone.now()
        future_offset_seconds = (
            2 + submit.max_q_length
        ) * runmodel.project.exp_task_time
        future_offset = datetime.timedelta(seconds=future_offset_seconds)
        expected_completion = cur_dt + future_offset
        runmodel.exp_comp_datetime = expected_completion
        runmodel.save()
        self.runmodel_instance = runmodel


def handle_submission(request, compute, submit_class, save_class):
    sub = submit_class(request, compute)
    if sub.badpost is not None:
        return sub.badpost
    elif sub.stop_submission:
        return PostResult(sub, None)
    else:
        save = save_class(sub)
        return PostResult(sub, save)
