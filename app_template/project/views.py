from webapp.apps.core.compute import Compute
from webapp.apps.core.views import (InputsView, EditInputsView, OutputsView,
                                    OutputsDownloadView)
from webapp.apps.core.models import Tag, TagOption

from .models import {Project}Run
from .displayer import {Project}Displayer
from .submit import {Project}Submit, {Project}Save
from .forms import {Project}InputsForm
from .meta_parameters import {project}_meta_parameters
from .constants import ({PROJECT}_VERSION, APP_NAME, APP_DESCRIPTION)


compute = Compute()


class {Project}InputsMixin:
    form_class = {Project}InputsForm
    displayer_class = {Project}Displayer
    submit_class = {Project}Submit
    save_class = {Project}Save
    project_name = "{Project-Title}"
    app_name = APP_NAME
    app_description = APP_DESCRIPTION
    meta_parameters = {project}_meta_parameters
    meta_options = []
    has_errors = False
    upstream_version = {PROJECT}_VERSION


class {Project}InputsView({Project}InputsMixin, InputsView):
    """
    A Django view for serving the default input page, validating the inputs,
    and submitting them to the backend worker nodes.
    """


class {Project}EditInputsView({Project}InputsMixin, EditInputsView):
    """
    A Django view for serving serving edited parameters.
    """
    model = {Project}Run


class {Project}OutputsView(OutputsView):
    """
    A Django view that polls the backend workers to check whether the result
    is ready yet. Once the result is ready, it is stored in the database and
    served from this view.
    """
    model = {Project}Run
    result_header = "{Project-Title} Results"
    tags = []
    aggr_tags = []


class {Project}OutputsDownloadView(OutputsDownloadView):
    """
    A Django view for downloading the result of the project run.
    """
    model = {Project}Run
