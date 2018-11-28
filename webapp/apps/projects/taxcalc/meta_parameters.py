from django import forms

from webapp.apps.core.meta_parameters import MetaParameters, MetaParameter
from .constants import START_YEAR, DEFAULT_SOURCE


meta_parameters = MetaParameters(
    parameters = [
        MetaParameter(
            name="start_year",
            default=START_YEAR,
            field=forms.IntegerField(min_value=2013, max_value=2018),
        ),
        MetaParameter(
            name="data_source",
            default=DEFAULT_SOURCE,
            field=forms.ChoiceField(choices=(("PUF", "PUF"), ("CPS", "CPS")))
        ),
        MetaParameter(
            name="use_full_sample",
            default=True,
            field=forms.BooleanField(required=False),
        )
    ]
)