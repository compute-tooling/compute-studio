from webapp.apps.core.submit import Submit, Save
from .forms import {Project}InputsForm
from .parser import {Project}Parser
from .models import {Project}Run
from .constants import {PROJECT}_VERSION, APP_NAME
from .meta_parameters import {project}_meta_parameters


class {Project}Submit(Submit):
    """
    High level logic for formatting the inputs, validating them, handling
    errors if they exist, and submitting to the backend workers.
    """
    parser_class = {Project}Parser
    form_class = {Project}InputsForm
    upstream_version = {PROJECT}_VERSION
    project = "{Project}"
    meta_parameters = {project}_meta_parameters
    app_name = APP_NAME

    def extend_data(self, data):
        data = super().extend_data(data)
        return data

class {Project}Save(Save):
    """
    Creates a Run Model instance for this model run.
    """
    project_name = "{Project}"
    runmodel = {Project}Run
