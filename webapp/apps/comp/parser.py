from collections import namedtuple

from webapp.apps.comp import actions
from webapp.apps.comp.compute import SyncCompute
from webapp.apps.comp.displayer import Displayer
from webapp.apps.comp.exceptions import AppError


ParamData = namedtuple("ParamData", ["name", "data"])


class ParameterLookUpException(Exception):
    pass


class BaseParser:
    def __init__(self, project, displayer, clean_inputs, **valid_meta_params):
        self.project = project
        self.clean_inputs = clean_inputs
        self.valid_meta_params = valid_meta_params
        for param, value in valid_meta_params.items():
            setattr(self, param, value)
        _, self.grouped_defaults = displayer.package_defaults()
        self.flat_defaults = {
            k: v for _, sect in self.grouped_defaults.items() for k, v in sect.items()
        }

    def parse_parameters(self):
        """
        Parse request and model objects and collect revisions and warnings
        This function is also called by dynamic/views.behavior_model.  In the
        future, this could be used as a generic GUI parameter parsing function.

        returns cleaned_inputs (grouped by major section), empty JSON string,
            empty errors/warnings dictionary
        """
        order_by_list_len = sorted(
            self.grouped_defaults,
            key=lambda k: len(self.grouped_defaults[k]),
            reverse=True,
        )

        inputs_by_section = {sect: {} for sect in self.grouped_defaults}
        for param, value in self.clean_inputs.items():
            if value in ("", None):
                continue
            for section in order_by_list_len:
                search_hit = self.get_default_param(
                    param, self.grouped_defaults[section], raise_error=False
                )
                if search_hit is not None:
                    inputs_by_section[section][search_hit.name] = value
                    break

        errors_warnings = {
            sect: {"errors": {}, "warnings": {}} for sect in inputs_by_section
        }
        errors_warnings["GUI"] = {"errors": {}, "warnings": {}}
        unflattened = {}
        for sect, inputs in inputs_by_section.items():
            uf, errors = self.unflatten(inputs)
            if errors["errors"]:
                errors_warnings["GUI"].update(errors)
            unflattened[sect] = uf
        return unflattened, errors_warnings

    def unflatten(self, parsed_input):
        """
        Does nothing by default, for now.
        """
        return parsed_input

    @staticmethod
    def get_default_param(param, defaults, param_get=None, raise_error=True):
        """
        Special logic is sometimes required for converting the parameter name
        from the name used in the webapp user-interface and the name specified
        by the project. See the taxcalcstyle ParamParser implementation for
        an example.
        """
        search_hit = defaults.get(param, None)
        if search_hit:
            return ParamData(param, search_hit)
        if raise_error:
            msg = "Received unexpected parameter: {}"
            raise ParameterLookUpException(msg.format(param))
        return None

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


class Parser(BaseParser):
    def parse_parameters(self):
        params, errors_warnings = super().parse_parameters()
        data = {
            "meta_param_dict": self.valid_meta_params,
            "adjustment": params,
            "errors_warnings": errors_warnings,
        }
        success, result = SyncCompute().submit_job(
            data, self.project.worker_ext(action=actions.PARSE)
        )
        if not success:
            raise AppError(params, result)
        result["GUI"].update(errors_warnings["GUI"])
        return params, result
