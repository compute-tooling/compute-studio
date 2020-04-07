from typing import NamedTuple, Type
from webapp.apps.comp.model_parameters import ModelParameters
from webapp.apps.comp.parser import Parser


class IOClasses(NamedTuple):
    model_parameters: ModelParameters
    Parser: Type[Parser]


def get_ioutils(project, **kwargs):
    return IOClasses(
        model_parameters=kwargs.get("ModelParameters", ModelParameters)(project),
        Parser=kwargs.get("Parser", Parser),
    )
