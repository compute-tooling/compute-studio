from typing import NamedTuple, Type
from webapp.apps.comp.displayer import Displayer
from webapp.apps.comp.parser import Parser


class IOClasses(NamedTuple):
    displayer: Displayer
    Parser: Type[Parser]


def get_ioutils(project, **kwargs):
    return IOClasses(
        displayer=kwargs.get("Displayer", Displayer)(project),
        Parser=kwargs.get("Parser", Parser),
    )
