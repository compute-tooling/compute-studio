from ..utils import IOClasses

from webapp.apps.comp.displayer import Displayer
from .param import ParamToolsParam
from .parser import ParamToolsParser

register = IOClasses(
    Param=ParamToolsParam, Parser=ParamToolsParser, Displayer=Displayer
)
