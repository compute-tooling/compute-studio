from webapp.apps.core.forms import InputsForm
from .displayer import CompbaseballDisplayer
from .meta_parameters import compbaseball_meta_parameters
from .models import CompbaseballInputs


class CompbaseballInputsForm(InputsForm):
    displayer_class = CompbaseballDisplayer
    model = CompbaseballInputs
    meta_parameters = compbaseball_meta_parameters
