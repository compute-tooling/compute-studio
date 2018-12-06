from webapp.apps.core.forms import InputsForm
from .displayer import {Project}Displayer
from .meta_parameters import {project}_meta_parameters
from .models import {Project}Inputs


class {Project}InputsForm(InputsForm):
    displayer_class = {Project}Displayer
    model = {Project}Inputs
    meta_parameters = {project}_meta_parameters
