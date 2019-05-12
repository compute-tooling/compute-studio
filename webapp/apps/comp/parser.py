from collections import namedtuple, defaultdict

from webapp.apps.comp import actions
from webapp.apps.comp.compute import SyncCompute
from webapp.apps.comp.displayer import Displayer
from webapp.apps.comp.exceptions import AppError
from webapp.apps.comp.utils import dims_to_dict, dims_to_string, is_reverse, is_wildcard


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
            uf = self.unflatten(inputs, errors_warnings)
            unflattened[sect] = uf
        return errors_warnings, unflattened

    def unflatten(self, parsed_input, errors_warnings):
        params = defaultdict(list)
        for param, value in parsed_input.items():
            basename, value_object = dims_to_dict(param, self.valid_meta_params)
            if value_object:
                value_object["value"] = value
                # Make sure meta parameter dimensions are updated.
                for mp, mp_val in self.valid_meta_params.items():
                    if mp in value_object:
                        value_object[mp] = mp_val
                params[basename].append(value_object)
            else:
                # No dimension information is encoded.
                params[param].append({"value": value})
        # only allow ops for models that have a year metaparam for now.
        if hasattr(self, "year"):
            return self.parse_ops(params, errors_warnings)
        else:
            return params

    def parse_ops(self, parsed_input, errors_warnings, extend="year"):
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

                        opped = {
                            extend: getattr(self, extend) - 1,
                            "value": val_obj["value"][i + 1],
                        }

                        revision[param].append(dict(val_obj, **opped))

                        # realign year and parameter indices
                        for _ in (0, number_reverse_operators + 1):
                            val_obj["value"].pop(0)
                        continue
                    else:
                        opped = {
                            extend: getattr(self, extend) + i,
                            "value": val_obj["value"][i],
                        }
                        revision[param].append(dict(val_obj, **opped))

                    i += 1
        return revision

    @staticmethod
    def get_default_param(param, defaults, param_get=None, raise_error=True):
        """
        Look up the parameter by its base name--without the dimension info
        attached. Return using the name with the dimension info attached.
        """
        if param.endswith("checkbox"):
            param_name = param.split("_checkbox")[0]
            if param_name in defaults:
                return ParamData(param, {})
        param_spl = param.split("____")
        search_hit = defaults.get(param_spl[0], None)
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
        errors_warnings, params = super().parse_parameters()
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
        if isinstance(result, (tuple, list)):
            result, *inputs_file = result
            inputs_file = inputs_file[0]
        else:
            inputs_file = None
        result["GUI"].update(errors_warnings["GUI"])
        return result, params, inputs_file
