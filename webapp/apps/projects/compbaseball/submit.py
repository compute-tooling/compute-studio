from webapp.apps.core.submit import Submit, Save
from .forms import CompbaseballInputsForm
from .parser import CompbaseballParser
from .models import CompbaseballRun
from .constants import COMPBASEBALL_VERSION, APP_NAME
from .meta_parameters import compbaseball_meta_parameters


class CompbaseballSubmit(Submit):
    """
    High level logic for formatting the inputs, validating them, handling
    errors if they exist, and submitting to the backend workers.
    """
    parser_class = CompbaseballParser
    form_class = CompbaseballInputsForm
    upstream_version = COMPBASEBALL_VERSION
    meta_parameters = compbaseball_meta_parameters
    app_name = APP_NAME

    def extend_data(self, data):
        data = super().extend_data(data)
        return data

class CompbaseballSave(Save):
    """
    Creates a Run Model instance for this model run.
    """
    project_name = "CompBaseball"
    runmodel = CompbaseballRun
