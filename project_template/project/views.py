from webapp.apps.core.compute import Compute
from webapp.apps.core.views import InputsView, OutputsView, OutputsDownloadView
from webapp.apps.core.models import Tag, TagOption

from .models import {Project}Run
from .displayer import {Project}Displayer
from .submit import {Project}Submit, {Project}Save
from .forms import {Project}InputsForm
from .meta_parameters import {project}_meta_parameters
from .constants import ({PROJECT}_VERSION)


compute = Compute()

class {Project}InputsView(InputsView):
    form_class = {Project}InputsForm
    displayer_class = {Project}Displayer
    submit_class = {Project}Submit
    save_class = {Project}Save
    result_header = "{Project} Results"
    project_name = "{Project}"
    app_name = "{project}"
    meta_parameters = {project}_meta_parameters
    meta_options = []
    has_errors = False
    upstream_version = {PROJECT}_VERSION


class {Project}OutputsView(OutputsView):
    model = {Project}Run
    result_header = "{Project} Results"
    dimension_name = "Dimension name here"
    tags = []
    aggr_tags = []


class {Project}OutputsDownloadView(OutputsDownloadView):
    model = {Project}Run
