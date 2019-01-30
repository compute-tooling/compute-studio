from webapp.apps.core.forms import InputsForm
from .displayer import MatchupsDisplayer
from .meta_parameters import matchups_meta_parameters
from .models import MatchupsInputs


class MatchupsInputsForm(InputsForm):
    displayer_class = MatchupsDisplayer
    model = MatchupsInputs
    meta_parameters = matchups_meta_parameters
