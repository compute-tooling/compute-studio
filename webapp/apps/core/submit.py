import ast
import datetime
from collections import namedtuple

from django.utils import timezone


from webapp.apps.users.models import Project
from webapp.apps.core.param_parser import ParamParser, append_errors_warnings
from webapp.apps.core.forms import InputsForm
from webapp.apps.core.constants import OUT_OF_RANGE_ERROR_MSG, WEBAPP_VERSION
from webapp.apps.core.models import CoreInputs

BadPost = namedtuple("BadPost", ["http_response_404", "has_errors"])
PostResult = namedtuple("PostResult", ["submit", "save"])

class Submit:

    Name = None
    ParamParserCls = ParamParser
    FormCls = InputsForm
    InputModelCls = None
    webapp_version = WEBAPP_VERSION
    upstream_version = None
    task_run_time_secs = None

    def __init__(self, request, compute, **kwargs):
        self.request = request
        self.compute = compute
        # TODO: what is this
        self.kwargs = kwargs
        self.model = None
        self.badpost = None

        self.get_fields()
        self.create_model()
        if self.badpost is not None:
            return
        if self.stop_submission:
            self.handle_errors()
        else:
            self.submit()

    def get_fields(self):
        fields = dict(self.request.GET)
        fields.update(dict(self.request.POST))
        fields = {
            k: v[0] if isinstance(v, list) else v
            for k, v in list(fields.items())
        }
        fields.pop("full_calc", None)
        self.has_errors = ast.literal_eval(fields["has_errors"])
        self.is_quick_calc = True if fields.get("quick_calc") else False
        fields["quick_calc"] = str(self.is_quick_calc)
        self.fields = fields
        self.meta_parameters = {"use_full_sample": not self.is_quick_calc}

    def create_model(self):
        self.form = self.FormCls(dict(self.fields, **self.meta_parameters))
        if self.form.non_field_errors():
            self.badpost = BadPost(
                http_response_404=HttpResponse("Bad Input!", status=400),
                has_errors=True,
            )
            return

        self.is_valid = self.form.is_valid()
        if self.is_valid:
            self.model = self.form.save(self.InputModelCls, commit=False)
            paramparser = self.ParamParserCls(
                self.model.gui_inputs,
                **self.meta_parameters
            )

            (
                upstream_parameters,
                upstream_json_files,
                errors_warnings,
            ) = paramparser.parse_parameters()
            self.model.upstream_parameters = upstream_parameters
            self.model.input_file = upstream_json_files
            self.model.errors_warnings = errors_warnings
            self.model.quick_calc = self.is_quick_calc
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
        if self.warn_msgs or self.error_msgs:
            self.form.add_error(None, OUT_OF_RANGE_ERROR_MSG)
            for input_type in self.model.errors_warnings:
                append_errors_warnings(
                    self.model.errors_warnings[input_type],
                    lambda param, msg: self.form.add_error(param, msg),
                )
        has_parse_errors = any(
            "Unrecognize value" in e[0]
            for e in list(self.form.errors.values())
        )
        if has_parse_errors:
            msg = (
                "Some fields have unrecognized values. Enter comma "
                "separated values for each input."
            )
            self.form.add_error(None, msg)

    def submit(self):
        data = dict({"user_mods": self.model.deserialized_inputs},
                    **self.meta_parameters)
        print('submit', data)
        self.data_list = self.extend_data(data)
        self.submitted_id, self.max_q_length = self.compute.submit_job(
            self.data_list, "taxcalc"
        )

    def extend_data(self, data):
        return [data]


class Save:

    ProjectName = None
    RunModelCls = None

    def __init__(self, submit):
        """
        Retrieve model run data from instance of `Submit`. Save to `RunModel`
        instance. Return that instance.

        Returns:
        --------
        RunModel
        """
        # create OutputUrl object
        runmodel = self.RunModelCls()
        runmodel.job_id = submit.submitted_id
        runmodel.inputs = submit.model
        runmodel.profile = submit.request.user.profile
        runmodel.project = Project.objects.get(name=self.ProjectName)

        runmodel.upstream_vers = submit.upstream_version
        runmodel.webapp_vers = submit.webapp_version

        cur_dt = timezone.now()
        future_offset_seconds = ((2 + submit.max_q_length) *
                                  submit.task_run_time_secs)
        future_offset = datetime.timedelta(seconds=future_offset_seconds)
        expected_completion = cur_dt + future_offset
        runmodel.exp_comp_datetime = expected_completion
        runmodel.save()
        self.runmodel = runmodel



def handle_submission(request, compute, SubmitCls, SaveCls, **kwargs):
    sub = SubmitCls(request, compute, **kwargs)
    if sub.badpost is not None:
        return sub.badpost
    elif sub.stop_submission:
        return PostResult(sub, None)
    else:
        save = SaveCls(sub)
        return PostResult(sub, save)