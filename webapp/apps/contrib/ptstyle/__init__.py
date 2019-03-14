from .displayer import ParamToolsDisplayer
from .param import ParamToolsParam
from .parser import ParamToolsParser


register = {
    "displayer": ParamToolsDisplayer,
    "param": ParamToolsParam,
    "parser": ParamToolsParser,
}
