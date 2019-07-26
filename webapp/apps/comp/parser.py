from collections import namedtuple, defaultdict
import time

from webapp.apps.comp import actions
from webapp.apps.comp.compute import Compute
from webapp.apps.comp.displayer import Displayer
from webapp.apps.comp.exceptions import AppError
from webapp.apps.comp.models import Inputs
from webapp.apps.comp.utils import dims_to_dict, dims_to_string, is_reverse, is_wildcard

ParamData = namedtuple("ParamData", ["name", "data"])


class ParameterLookUpException(Exception):
    pass


def parse_ops(self, parsed_input, errors_warnings, extend, extend_val):
    """
    Parses and applies the * and < operators on *specific projects*.
    This will be superseded by a better GUI.
    """
    number_reverse_operators = 1

    revision = defaultdict(list)
    for param in parsed_input:
        if param.endswith("checkbox"):
            revision[param] = parsed_input[param]
            continue
        for val_obj in parsed_input[param]:
            i = 0
            if not isinstance(val_obj["value"], list):
                revision[param].append(val_obj)
                continue
            while i < len(val_obj["value"]):
                if is_wildcard(val_obj["value"][i]):
                    # may need to do something here
                    pass
                elif is_reverse(val_obj["value"][i]):
                    # only the first character can be a reverse char
                    # and there must be a following character
                    # TODO: Handle error
                    if i != 0:
                        errors_warnings["GUI"]["errors"][param] = [
                            "Reverse operator can only be used in the first position."
                        ]
                        return {}
                    if len(val_obj["value"]) == 1:
                        errors_warnings["GUI"]["errors"][param] = [
                            "Reverse operator must have an additional value, e.g. '<,2'"
                        ]
                        return {}
                    # set value for parameter in start_year - 1

                    opped = {extend: extend_val - 1, "value": val_obj["value"][i + 1]}

                    revision[param].append(dict(val_obj, **opped))

                    # realign year and parameter indices
                    for _ in (0, number_reverse_operators + 1):
                        val_obj["value"].pop(0)
                    continue
                else:
                    opped = {extend: extend_val + i, "value": val_obj["value"][i]}
                    revision[param].append(dict(val_obj, **opped))

                i += 1
    return revision


class BaseParser:
    def __init__(
        self,
        project,
        displayer,
        clean_inputs,
        extend=False,
        compute=None,
        **valid_meta_params,
    ):
        self.project = project
        self.clean_inputs = clean_inputs
        self.compute = compute or Compute()
        self.valid_meta_params = valid_meta_params
        self.extend = extend
        for param, value in valid_meta_params.items():
            setattr(self, param, value)
        defaults = displayer.package_defaults()
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
            if self.extend and hasattr(self, "year"):
                adjustment[sect] = parse_ops(
                    adjustmnet[sect], errors_warnings, "year", self.year
                )

        # kick off async parsing
        job_id, queue_length = self.post(errors_warnings, adjustment)

        return {
            "job_id": job_id,
            "queue_length": queue_length,
            "adjustment": adjustment,
            "errors_warnings": errors_warnings,
            "inputs_file": None,
        }
