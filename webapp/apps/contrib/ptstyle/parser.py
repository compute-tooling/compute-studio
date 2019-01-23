from collections import defaultdict

from webapp.apps.core.parser import Parser, ParamData, ParameterLookUpException


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
            # Split into name and dimension components.
            spl = param.split("___")
            # len(spl) > 1 implies dimension info is in the second component
            if len(spl) > 1:
                assert len(spl) == 2
                base_name, dims = spl
                # Split dimension component by each dimension
                dimstrings = dims.split("__")
                value_item = {}
                # Further parse those down into the name of the dimension
                # and its value.
                for dim in dimstrings:
                    dim_name, dim_value = dim.split("_")
                    value_item[dim_name] = dim_value
                value_item["value"] = value
                # Make sure meta parameter dimensions are updated.
                for mp, mp_val in self.valid_meta_params.items():
                    if mp in value_item:
                        value_item[mp] = mp_val
                params[base_name].append(value_item)
            else:
                # No dimension information is encoded.
                assert len(spl) == 1
                params[param].append({"value": value})
        return params