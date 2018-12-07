from webapp.apps.core.parser import Parser
from .displayer import CompbaseballDisplayer


class CompbaseballParser(Parser):
    """
    Formats the parameters into the format defined by the upstream project,
    calls the upstream project's validation functions, and formats the errors
    if they exist.
    """
    displayer_class = CompbaseballDisplayer