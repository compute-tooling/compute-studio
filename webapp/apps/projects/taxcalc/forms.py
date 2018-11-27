from django import forms

from webapp.apps.core.forms import Form, MetaParam
from .constants import START_YEAR, DEFAULT_SOURCE



class TaxcalcForm(Form):
    meta_parameters = [
        MetaParam(
            name="start_year",
            default=START_YEAR,
            FieldCls=forms.IntegerField(min_value=2013, max_value=2018),
        ),
        MetaParam(
            name="data_source",
            default=DEFAULT_SOURCE,
            FieldCls=forms.CharField(max_length=3)
        )
    ]
