from ..utils import IOClasses
from .param import TaxcalcStyleParam
from .parser import TaxcalcStyleParser
from webapp.apps.comp.displayer import Displayer


register = IOClasses(
    Displayer=Displayer, Param=TaxcalcStyleParam, Parser=TaxcalcStyleParser
)
