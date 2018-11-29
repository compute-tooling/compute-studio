from django import forms

from webapp.apps.core.meta_parameters import MetaParameters, MetaParameter
from .constants import START_YEAR, DEFAULT_SOURCE, START_YEARS, DATA_SOURCES


meta_parameters = MetaParameters(
    parameters = [
        MetaParameter(
            name="start_year",
            default=START_YEAR,
            field=forms.TypedChoiceField(coerce=lambda val: int(val),
                                         choices=list((i, i) for i in START_YEARS)),
        ),
        MetaParameter(
            name="data_source",
            default=DEFAULT_SOURCE,
            field=forms.ChoiceField(choices=list((i, i) for i in DATA_SOURCES))
        ),
        MetaParameter(
            name="use_full_sample",
            default=True,
            field=forms.TypedChoiceField(coerce=lambda val: bool(val),
                                         choices=list((i, i) for i in (True, False))),
        )
    ]
)