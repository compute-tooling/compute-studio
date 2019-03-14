from ..utils import IOClasses

from .displayer import ParamToolsDisplayer
from .param import ParamToolsParam
from .parser import ParamToolsParser

register = IOClasses(
    Displayer=ParamToolsDisplayer, Param=ParamToolsParam, Parser=ParamToolsParser
)
