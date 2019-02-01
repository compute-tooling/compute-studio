from collections import defaultdict

from webapp.apps.core.parser import Parser, ParamData, ParameterLookUpException
from .utils import to_dict

class ParamToolsParser(Parser):

    @staticmethod
    def get_default_param(param, defaults, param_get=None, raise_error=True):
        """
        Look up the parameter by its base name--without the dimension info
        attached. Return using the name with the dimension info attached.
        """
        param_spl = param.split("___")
        search_hit = defaults.get(param_spl[0], None)
        if search_hit:
            return ParamData(param, search_hit)
        if raise_error:
            msg = "Received unexpected parameter: {}"
            raise ParameterLookUpException(msg.format(param))
        return None

    def unflatten(self, parsed_input):
        params = defaultdict(list)
        for param, value in parsed_input.items():
            basename, value_object = to_dict(param)
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
        return params