from webapp.apps.contrib.taxcalcstyle import param_parser
from .param_displayer import ParamDisplayer


class ParamParser(param_parser.ParamParser):
    ParamDisplayerCls = ParamDisplayer
