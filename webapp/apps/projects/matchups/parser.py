from webapp.apps.core.parser import Parser
from .displayer import MatchupsDisplayer

import matchups


class MatchupsParser(Parser):
    """
    Formats the parameters into the format defined by the upstream project,
    calls the upstream project's validation functions, and formats the errors
    if they exist.
    """
    displayer_class = MatchupsDisplayer

    def parse_parameters(self):
        params, jsonparams, errors_warnings = super().parse_parameters()

        ###################################
        # code snippet
        # code snippet
        def parse_user_inputs(params, jsonparams, errors_warnings,
                              **meta_parameters):
            # parse the params, jsonparams, and errors_warnings further
            use_2018 = meta_parameters["use_2018"]
            params, jsonparams, errors_warnings = matchups.parse_inputs(
                params, jsonparams, errors_warnings, use_2018=use_2018)
            return params, jsonparams, errors_warnings
        ####################################

        return parse_user_inputs(params, jsonparams, errors_warnings,
                                 **self.valid_meta_params)