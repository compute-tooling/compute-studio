from typing import NamedTuple, Type
from webapp.apps.contrib.ptstyle import Displayer, Param, Parser


class IOClasses(NamedTuple):
    displayer: Displayer
    Param: Type[Param]
    Parser: Type[Parser]


def get_ioutils(project, **kwargs):
    return IOClasses(
        displayer=kwargs.get("Displayer", Displayer)(
            project, kwargs.get("Param", Param)
        ),
        Param=kwargs.get("Param", Param),
        Parser=kwargs.get("Parser", Parser),
    )
