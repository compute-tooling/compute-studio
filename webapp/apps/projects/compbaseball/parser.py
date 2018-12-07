from webapp.apps.core.parser import Parser
from .displayer import CompbaseballDisplayer

from compbaseball import baseball

class CompbaseballParser(Parser):
    """
    Formats the parameters into the format defined by the upstream project,
    calls the upstream project's validation functions, and formats the errors
    if they exist.
    """
    displayer_class = CompbaseballDisplayer

    def parse_parameters(self):
        params, _, _ = super().parse_parameters()
        params, jsonstrs, errors_warnings = baseball.parse_inputs(params)
        return params, jsonstrs, errors_warnings