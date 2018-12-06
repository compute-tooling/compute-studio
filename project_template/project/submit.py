from webapp.apps.core.submit import Submit, Save
from .forms import {Project}InputsForm
from .parser import {Project}Parser
from .models import {Project}Run
from .constants import {PROJECT}_VERSION
from .meta_parameters import {project}_meta_parameters


class {Project}Submit(Submit):
    parser_class = {Project}Parser
    form_class = {Project}InputsForm
    upstream_version = {PROJECT}_VERSION
    project = "{Project}"
    meta_parameters = {project}_meta_parameters

    def extend_data(self, data):
        data = super().extend_data()
        return data

class {Project}Save(Save):
    project_name = "{Project}"
    runmodel = {Project}Run
