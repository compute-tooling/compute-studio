from django import forms

from webapp.apps.core.forms import InputsForm, MetaParam
from .param_displayer import ParamDisplayer
from .constants import START_YEAR, DEFAULT_SOURCE



class TaxcalcInputsForm(InputsForm):
    ParamDisplayerCls = ParamDisplayer
    meta_parameters = [
        MetaParam(
            name="start_year",
            default=START_YEAR,
            field=forms.IntegerField(min_value=2013, max_value=2018),
        ),
        MetaParam(
            name="data_source",
            default=DEFAULT_SOURCE,
            field=forms.CharField(max_length=3)
        )
    ]
