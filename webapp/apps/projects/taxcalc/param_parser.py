from collections import defaultdict, namedtuple
import json

from django.forms import NullBooleanSelect

import taxcalc

from .helpers import is_wildcard, is_reverse
from webapp.apps.projects.taxcalc.param_displayer import ParamDisplayer

MetaParam = namedtuple("MetaParam", ["param_name", "param_meta"])
CPI_WIDGET = NullBooleanSelect()


class ParameterLookUpException(Exception):
    pass


class ParamParser:
    def __init__(self, raw_input, **meta_parameters):
        self.raw_input = raw_input
        for param, value in meta_parameters.items():
            setattr(self, param, value)
        self.grouped_defaults = ParamDisplayer(
            **meta_parameters
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
            if not value:
                continue
            success = False
            for section in order_by_list_len:
                search_hit = self.get_default_param(
                    param, self.grouped_defaults[section], raise_error=False
                )
                if search_hit is not None:
                    inputs_by_section[section][search_hit.param_name] = value
                    success = True
                    break
            # unable to match parameter, so raise error
            failed_lookups.append(param)

        return inputs_by_section, failed_lookups

    def unflatten(self, parsed_input):  # to_json_reform
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
        number_reverse_operators = 1

        revision = {}
        for param in parsed_input:
            revision[param] = {}
            if not isinstance(parsed_input[param], list):
                assert isinstance(
                    parsed_input[param], bool
                ) and param.endswith("_cpi")
                revision[param][str(self.start_year)] = parsed_input[param]
                continue
            i = 0
            while i < len(parsed_input[param]):
                if is_wildcard(parsed_input[param][i]):
                    # may need to do something here
                    pass
                elif is_reverse(parsed_input[param][i]):
                    # only the first character can be a reverse char
                    # and there must be a following character
                    assert len(parsed_input[param]) > 1
                    # set value for parameter in start_year - 1
                    assert isinstance(
                        parsed_input[param][i + 1], (int, float)
                    ) or isinstance(parsed_input[param][i + 1], bool)
                    revision[param][str(self.start_year - 1)] = [
                        parsed_input[param][i + 1]
                    ]

                    # realign year and parameter indices
                    for op in (0, number_reverse_operators + 1):
                        parsed_input[param].pop(0)
                    continue
                else:
                    assert isinstance(
                        parsed_input[param][i], (int, float)
                    ) or isinstance(parsed_input[param][i], bool)
                    revision[param][str(self.start_year + i)] = [
                        parsed_input[param][i]
                    ]

                i += 1

        return revision

    def check_revisions_for_errors(
        self, policy_inputs_json, assumption_inputs_json
    ):
        """
        Read reform and parse errors
        returns reform and assumption dictionaries that are compatible with
                taxcalc.Policy.implement_reform
                parsed warning and error messsages to be displayed on input page
                if necessary
        """
        policy_dict = taxcalc.Calculator.read_json_param_objects(
            policy_inputs_json, assumption_inputs_json
        )
        # get errors and warnings on parameters that do not cause ValueErrors
        tc_errors_warnings = taxcalc.tbi.reform_warnings_errors(
            policy_dict, self.use_puf_not_cps
        )
        # errors_warnings contains warnings and errors separated by each
        # project/project module
        errors_warnings = {}
        for project in tc_errors_warnings:
            errors_warnings[project] = self.parse_errors_warnings(
                tc_errors_warnings[project]
            )

        # separate reform and assumptions
        reform_dict = policy_dict["policy"]
        assumptions_dict = {
            k: v for k, v in list(policy_dict.items()) if k != "policy"
        }

        return reform_dict, assumptions_dict, errors_warnings

    @staticmethod
    def get_default_param(param, defaults, param_get=None, raise_error=True):
        """
        Map webapp field name to Upstream package parameter name. This is a
        static method because:
        1. it doesn't access any Instance or Class data
        2. it is used as a standalone method to make sure parameter names exist
        3. it is not simply a function because inheriting classes may want to
            override it.

        For example: STD_0 maps to _STD_single

        returns: named tuple with taxcalc param name and metadata
        """
        if param_get is None:
            param_get = lambda d, k: d[k] if k is not None else d
        if param in defaults:  # ex. EITC_indiv --> _EITC_indiv
            return MetaParam(param, param_get(defaults[param], None))
        param_pieces = param.split("_")
        end_piece = param_pieces[-1]
        no_suffix = "_".join(param_pieces[:-1])
        if end_piece == "cpi":  # ex. SS_Earnings_c_cpi --> _SS_Earnings_c_cpi
            if no_suffix in defaults:
                return MetaParam(param, param_get(defaults[no_suffix], None))
            else:
                if raise_error:
                    msg = "Received unexpected parameter: {}"
                    raise ParameterLookUpException(msg.format(param))
                return None
        if no_suffix in defaults:  # ex. STD_0 --> _STD_single
            try:
                ix = int(end_piece)
            except ValueError:
                if raise_error:
                    msg = "Parsing {}: Expected integer for index but got {}"
                    raise ParameterLookUpException(msg.format(param, end_piece))
                return None
            num_columns = len(param_get(defaults[no_suffix], "col_label"))
            if ix < 0 or ix >= num_columns:
                if raise_error:
                    msg = "Parsing {}: Index {} not in range ({}, {})"
                    raise ParameterLookUpException(
                        msg.format(param, ix, 0, num_columns)
                    )
                return None
            col_label = param_get(defaults[no_suffix], "col_label")[ix]
            return MetaParam(
                no_suffix + "_" + col_label, param_get(defaults[no_suffix], None)
            )
        if raise_error:
            msg = "Received unexpected parameter: {}"
            raise ParameterLookUpException(msg.format(param))
        return None

    def parse_errors_warnings(self, errors_warnings):
        """
        Parse error messages so that they can be mapped to webapp param ID. This
        allows the messages to be displayed under the field where the value is
        entered.

        returns: dictionary 'parsed' with keys: 'errors' and 'warnings'
            parsed['errors/warnings'] = {year: {tb_param_name: 'error message'}}
        """
        parsed = {"errors": defaultdict(dict), "warnings": defaultdict(dict)}
        for action in errors_warnings:
            msgs = errors_warnings[action]
            if len(msgs) == 0:
                continue
            for msg in msgs.split("\n"):
                if len(msg) == 0:  # new line
                    continue
                msg_spl = msg.split()
                msg_action = msg_spl[0]
                year = msg_spl[1]
                curr_id = msg_spl[2]
                msg_parse = msg_spl[2:]
                parsed[action][curr_id][year] = " ".join(
                    [msg_action] + msg_parse + ["for", year]
                )
        return parsed


class GUIParamParser(ParamParser):
    def __init__(self, raw_input, **meta_parameters):
        super().__init__(raw_input, **meta_parameters)

    def parse_parameters(self):
        """
        Implement custom parameter parsing logic
        """
        inputs_by_section, failed_lookups = super().parse_parameters()

        flat_policy_inputs = inputs_by_section["policy"]
        flat_behavior_inputs = inputs_by_section["behavior"]
        if flat_policy_inputs is not None:
            policy_inputs = self.unflatten(flat_policy_inputs)
        if flat_behavior_inputs is not None:
            behavior_inputs = self.unflatten(flat_behavior_inputs)

        policy_inputs = {"policy": policy_inputs}

        policy_inputs_json = json.dumps(policy_inputs, indent=4)

        assumption_inputs = {
            "behavior": behavior_inputs,
            "growdiff_response": {},
            "consumption": {},
            "growdiff_baseline": {},
            "growmodel": {},
        }

        assumption_inputs_json = json.dumps(assumption_inputs, indent=4)

        (
            policy_dict,
            assumptions_dict,
            errors_warnings,
        ) = self.check_revisions_for_errors(
            policy_inputs_json,
            assumption_inputs_json,
        )
        params = {"policy": policy_dict, **assumptions_dict}
        jsonstrs = {"policy": policy_inputs, "assumptions": assumption_inputs}
        return (
            params,
            jsonstrs,
            errors_warnings,
        )


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