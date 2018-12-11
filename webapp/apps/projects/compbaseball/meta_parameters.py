from django import forms

from webapp.apps.core.meta_parameters import (meta_parameters, MetaParameters,
                                              MetaParameter)

"""
A module for defining this project's "meta-parameters." One way to think of
these parameters is as control parameters. They define some base conditions for
the inputs parameter space. One example is a start year for a project where
many parameters values are temporal in nature.

For now, COMP is opinionated about which Django Form Fields* are used and
how they are used. See ______ for a list of use cases and associated fields
and usages. In the future, a more mature and feature-complete COMP may become
less opionated.

* not to be confused with Django Model Fields!

Define this project's meta_parameters like this:

```python
def meta_parameter_factory(mp):
    mp.parameters = [
        MetaParameter(
            name="pitcher",
            default="Clayton Kershaw",
            field = forms.CharField(max_length=100)
        ),
        MetaParameter(
            name="start_date",
            default=datetime.date(2018, 8, 01),
            field = forms.CharField(max_length=100)
        ),
        MetaParameter(
            name="is_a_dodger",
            default=True,
            field=forms.TypedChoiceField(coerce=coerce_bool,
                                         choices=list((i, i) for i in (True, False))),
        ),
    ]
    return mp
```

"""

def meta_parameter_factory(mp):
    # optionally edit parameters attribute on mp
    return mp


compbaseball_meta_parameters = meta_parameter_factory(meta_parameters)