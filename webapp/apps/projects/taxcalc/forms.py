from webapp.apps.core.forms import InputsForm
from .displayer import TaxcalcDisplayer
from .meta_parameters import meta_parameters
from .models import TaxcalcInputs


class TaxcalcInputsForm(InputsForm):
    displayer_class = TaxcalcDisplayer
    model = TaxcalcInputs
    meta_parameters = meta_parameters
