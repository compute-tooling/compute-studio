from django import forms

from webapp.apps.core.fields import coerce_bool
from webapp.apps.core.meta_parameters import (
    MetaParameter,
    MetaParameters,
    translate_to_django,
)


def test_meta_parameters_instance():
    meta_parameters = MetaParameters()
    assert meta_parameters
    assert meta_parameters.parameters == []


def test_meta_parameters():
    meta_parameters = MetaParameters(
        [
            MetaParameter(
                name="inttest", title="Int test", default=1, field=forms.IntegerField()
            ),
            MetaParameter(
                name="booltest",
                title="bool test",
                default=True,
                field=forms.BooleanField(required=False),
            ),
        ]
    )
    valid = meta_parameters.validate({"inttest": "2", "booltest": False})
    assert valid["inttest"] == 2
    assert valid["booltest"] is False
    valid = meta_parameters.validate({"booltest": False})
    assert valid["inttest"] == 1
    assert valid["booltest"] is False


def test_translate():
    metaparameters = {
        "meta_parameters": {
            "use_full_data": {
                "title": "Use full data",
                "default": True,
                "type": "bool",
                "validators": {},
            }
        }
    }
    result = translate_to_django(metaparameters)

    mp = result.parameters[0]
    assert mp.title == "Use full data"
    assert mp.name == "use_full_data"
    assert mp.default == True
    assert isinstance(mp.field, forms.TypedChoiceField)
