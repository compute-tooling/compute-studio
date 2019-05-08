from collections import defaultdict

from webapp.apps.comp.parser import Parser, ParamData, ParameterLookUpException
from .utils import dims_to_dict


def parse_ops(self, parsed_input, extend="year"):
    """
    Convert fields style dictionary to json reform style dictionary
    For example:
    start_year = 2017, cls = taxcalc.Policy
    fields = {'_CG_nodiff': [False]},
            '_FICA_ss_trt': ["*", 0.1, "*", 0.2],
            '_ID_Charity_c_cpi': True,
            '_EITC_rt_2kids': [1.0]}
    to
    revision = {'_CG_nodiff': {'2017': [False]},
                '_FICA_ss_trt': {'2020': [0.2], '2018': [0.1]},
                '_ID_Charity_c_cpi': {'2017': True},
                '_EITC_rt_2kids': {'2017': [1.0]}}
    returns: json style revision
    """
    errors = {"errors": {}}
    number_reverse_operators = 1

    revision = {}
    for param in parsed_input:
        revision[param] = {}
        if param.endswith("checkbox"):
            revision[param] = parsed_input[param]
            continue
        i = 0
        while i < len(parsed_input[param]):
            if is_wildcard(parsed_input[param][i]["value"]):
                # may need to do something here
                pass
            elif is_reverse(parsed_input[param][i]["value"]):
                # only the first character can be a reverse char
                # and there must be a following character
                assert len(parsed_input[param]) > 1
                # set value for parameter in start_year - 1

                # get match dim name and value for labels not equal to the
                # extend label or "value"
                to_match = {
                    extend: getattr(self, extend) - 1,
                    **{
                        label: val
                        for label, val in parsed_input[param][i].items()
                        if label not in ("value", extend)
                    },
                }
                match = [
                    data
                    for data in parsed_input[param]
                    if (to_match[label] == data[label] for label in to_match)
                ]
                if not match:
                    errors["errors"][param] = "No match when using the < operator."
                    return parsed_input, errors

                revision[param] = match

                # realign year and parameter indices
                for op in (0, number_reverse_operators + 1):
                    parsed_input[param].pop(0)
                continue
            else:
                revision[param] = parsed_input[param][i]
            i += 1
    return revision, errors


class ParamToolsParser(Parser):
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

    def unflatten(self, parsed_input):
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
        if self.project.title == "Tax-Brain":
            return parse_ops(params)
        else:
            return params, {"errors": []}
