from django import forms

from webapp.apps.core.meta_parameters import (MetaParameter, MetaParameters)

def test_meta_parameters_instance():
    meta_parameters = MetaParameters()
    assert meta_parameters
    assert meta_parameters.parameters == []

def test_meta_parameters():
    meta_parameters = MetaParameters([
        MetaParameter(
            name="inttest",
            default=1,
            field = forms.IntegerField()
        ),
        MetaParameter(
            name="booltest",
            default=True,
            field = forms.BooleanField(required=False)
        )
    ])
    valid = meta_parameters.validate({"inttest": "2", "booltest": False})
    assert valid["inttest"] == 2
    assert valid["booltest"] is False
    valid = meta_parameters.validate({"booltest": False})
    assert valid["inttest"] == 1
    assert valid["booltest"] is False
