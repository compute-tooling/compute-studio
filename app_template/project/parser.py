from webapp.apps.core.parser import Parser
from .displayer import {Project}Displayer


class {Project}Parser(Parser):
    """
    Formats the parameters into the format defined by the upstream project,
    calls the upstream project's validation functions, and formats the errors
    if they exist.
    """
    displayer_class = {Project}Displayer

    def parse_parameters(self):
        params, jsonparams, errors_warnings = super().parse_parameters()

        ###################################
        # code snippet

        ####################################

        return parse_user_inputs(params, jsonparams, errors_warnings,
                                 **self.valid_meta_params)