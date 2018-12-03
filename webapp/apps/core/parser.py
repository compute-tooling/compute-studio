from collections import defaultdict, namedtuple
from webapp.apps.core.displayer import Displayer


ParamData = namedtuple("ParamData", ["name", "data"])


class ParameterLookUpException(Exception):
    pass


class Parser:
    displayer_class = Displayer

    def __init__(self, clean_inputs, **valid_meta_params):
        self.clean_inputs = clean_inputs
        for param, value in valid_meta_params.items():
            setattr(self, param, value)
        displayer = self.displayer_class(
            **valid_meta_params
        )
        self.grouped_defaults = displayer.package_defaults()
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
            if value in ('', None):
                continue
            for section in order_by_list_len:
                search_hit = self.get_default_param(
                    param, self.grouped_defaults[section], raise_error=False
                )
                if search_hit is not None:
                    inputs_by_section[section][search_hit.name] = value
                    success = True
                    break

        unflattened = {}
        for sect, inputs in inputs_by_section.items():
            unflattened[sect] = self.unflatten(inputs)

        return unflattened, "", {}

    def unflatten(self, parsed_input):
        """
        Does nothing by default, for now.
        """
        return parsed_input

    def check_revisions_for_errors(self, *args, **kwargs):
        """
        Does nothing by default, for now.
        """
        return {}

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
    def parse_errors_warnings(errors_warnings):
        """
        Custom logic can be added here if the error messages need to be
        converted to the COMP errors_warnings criteria.
        """
        return errors_warnings

    @staticmethod
    def append_errors_warnings(errors_warnings, append_func):
        """
        Appends warning/error messages to some object, append_obj, according to
        the provided function, append_func
        """
        for action in ["warnings", "errors"]:
            for param in errors_warnings[action]:
                msg = errors_warnings[action][param]
                append_func(param, msg)