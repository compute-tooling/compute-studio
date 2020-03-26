from collections import namedtuple, defaultdict
import time

from webapp.apps.comp import actions
from webapp.apps.comp.compute import Compute
from webapp.apps.comp.exceptions import AppError
from webapp.apps.comp.models import Inputs

ParamData = namedtuple("ParamData", ["name", "data"])


class ParameterLookUpException(Exception):
    pass


class BaseParser:
    def __init__(
        self, project, model_parameters, clean_inputs, compute=None, **valid_meta_params
    ):
        self.project = project
        self.clean_inputs = clean_inputs
        self.compute = compute or Compute()
        self.valid_meta_params = valid_meta_params
        for param, value in valid_meta_params.items():
            setattr(self, param, value)
        defaults = model_parameters.defaults(self.valid_meta_params)
        self.grouped_defaults = defaults["model_parameters"]
        self.flat_defaults = {
            k: v for _, sect in self.grouped_defaults.items() for k, v in sect.items()
        }

    @staticmethod
    def append_errors_warnings(errors_warnings, append_func, defaults=None):
        """
        Appends warning/error messages to some object, append_obj, according to
        the provided function, append_func
        """
        for action in ["warnings", "errors"]:
            for param in errors_warnings[action]:
                msg = errors_warnings[action][param]
                append_func(param, msg, defaults)

    def parse_parameters(self):
        errors_warnings = {
            sect: {"errors": {}, "warnings": {}}
            for sect in list(self.grouped_defaults) + ["GUI", "API"]
        }
        adjustment = {sect: {} for sect in self.grouped_defaults}
        return errors_warnings, adjustment

    def post(self, errors_warnings, params):
        data = {
            "meta_param_dict": self.valid_meta_params,
            "adjustment": params,
            "errors_warnings": errors_warnings,
        }
        job_id, queue_length = self.compute.submit_job(
            data, self.project.worker_ext(action=actions.PARSE)
        )
        return job_id, queue_length


class Parser:
    pass


class APIParser(BaseParser):
    def parse_parameters(self):
        errors_warnings, adjustment = super().parse_parameters()
        extra_keys = set(self.clean_inputs.keys() - self.grouped_defaults.keys())
        if extra_keys:
            errors_warnings["API"]["errors"] = {
                "extra_keys": [f"Has extra sections: {' ,'.join(extra_keys)}"]
            }

        for sect in adjustment:
            adjustment[sect].update(self.clean_inputs.get(sect, {}))

        # kick off async parsing
        job_id, queue_length = self.post(errors_warnings, adjustment)
        return {
            "job_id": job_id,
            "queue_length": queue_length,
            "adjustment": adjustment,
            "errors_warnings": errors_warnings,
            "custom_adjustment": None,
        }
