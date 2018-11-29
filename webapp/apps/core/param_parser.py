from collections import defaultdict
from webapp.apps.core.param_displayer import ParamDisplayer

class ParameterLookUpException(Exception):
    pass


class ParamParser:
    ParamDisplayerCls = ParamDisplayer

    def __init__(self, raw_input, **valid_meta_params):
        self.raw_input = raw_input
        for param, value in valid_meta_params.items():
            setattr(self, param, value)
        self.grouped_defaults = self.ParamDisplayerCls(
            **valid_meta_params
        ).package_defaults()
        self.flat_defaults = {
            k: v
            for _, sect in self.grouped_defaults.items()
            for k, v in sect.items()
        }

    def parse_parameters(self):
        """
        Parse request and model objects and collect revisions and warnings
        This function is also called by dynamic/views.behavior_model.  In the
        future, this could be used as a generic GUI parameter parsing function.

        returns revision dictionaries that are compatible with
                taxcalc.Policy.implement_reform
                raw revision and assumptions text
                parsed warning and error messsages to be displayed on input page
                if necessary
        """
        order_by_list_len = sorted(
            self.grouped_defaults,
            key=lambda k: len(self.grouped_defaults[k]),
            reverse=True,
        )

        inputs_by_section = defaultdict(dict)
        failed_lookups = [] # TODO: deal with failed lookups
        for param, value in self.raw_input.items():
            if value in ('', None):
                continue
            success = False
            for section in order_by_list_len:
                search_hit = self.get_default_param(
                    param, self.grouped_defaults[section], raise_error=False
                )
                if search_hit is not None:
                    inputs_by_section[section][search_hit.name] = value
                    success = True
                    break
            # unable to match parameter, so raise error
            failed_lookups.append(param)

        return inputs_by_section, failed_lookups

    def unflatten(self, parsed_input):
        raise NotImplementedError()

    def check_revisions_for_errors(self, *args, **kwargs):
        raise NotImplementedError()

    @staticmethod
    def get_default_param(param, defaults, param_get=None, raise_error=True):
        raise NotImplementedError()

    @staticmethod
    def parse_errors_warnings(errors_warnings):
        raise NotImplementedError()

def append_errors_warnings(errors_warnings, append_func):
    """
    Appends warning/error messages to some object, append_obj, according to
    the provided function, append_func
    """
    for action in ["warnings", "errors"]:
        for param in errors_warnings[action]:
            for year in sorted(
                list(errors_warnings[action][param].keys()),
                key=lambda x: int(x),
            ):
                msg = errors_warnings[action][param][year]
                append_func(param, msg)