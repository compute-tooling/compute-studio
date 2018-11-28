from django import forms

from webapp.apps.core.forms import InputsForm
from .param_displayer import ParamDisplayer
from .meta_parameters import meta_parameters


class TaxcalcInputsForm(InputsForm):
    ParamDisplayerCls = ParamDisplayer
    meta_parameters = meta_parameters
