from webapp.apps.core.submit import Submit, Save
from .forms import MatchupsInputsForm
from .parser import MatchupsParser
from .models import MatchupsRun
from .constants import MATCHUPS_VERSION, APP_NAME
from .meta_parameters import matchups_meta_parameters


class MatchupsSubmit(Submit):
    """
    High level logic for formatting the inputs, validating them, handling
    errors if they exist, and submitting to the backend workers.
    """
    parser_class = MatchupsParser
    form_class = MatchupsInputsForm
    upstream_version = MATCHUPS_VERSION
    meta_parameters = matchups_meta_parameters
    app_name = APP_NAME

    def extend_data(self, data):
        data = super().extend_data(data)
        return data

class MatchupsSave(Save):
    """
    Creates a Run Model instance for this model run.
    """
    project_name = "Matchups"
    runmodel = MatchupsRun
