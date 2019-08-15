from django import forms

from webapp.apps.comp.meta_parameters import (
    coerce_bool,
    MetaParameter,
    MetaParameters,
    translate_to_django,
)


def test_meta_parameters_instance():
    meta_parameters = MetaParameters()
    assert meta_parameters
    assert meta_parameters.parameters == {}


def test_meta_parameters():
    meta_parameters = MetaParameters(
        parameters={
            "inttest": MetaParameter(
                title="Int test",
                description="An int test",
                value=1,
                field=forms.IntegerField(),
            ),
            "booltest": MetaParameter(
                description="a bool test",
                title="A bool test",
                value=True,
                field=forms.BooleanField(required=False),
            ),
        }
    )
    valid = meta_parameters.validate({"inttest": "2", "booltest": False})
    assert valid["inttest"] == 2
    assert valid["booltest"] is False
    valid = meta_parameters.validate({"booltest": False})
    assert valid["inttest"] == 1
    assert valid["booltest"] is False


def test_translate():
    metaparameters = {
        "use_full_data": {
            "title": "Use full data",
            "description": "use full data...",
            "value": True,
            "type": "bool",
            "validators": {},
        }
    }
    result = translate_to_django(metaparameters)

    mp = next(v for v in result.parameters.values())
    assert mp.title == "Use full data"
    assert next(k for k in result.parameters.keys()) == "use_full_data"
    assert mp.value == True
    assert isinstance(mp.field, forms.TypedChoiceField)


def test_coerce_bool():
    assert coerce_bool("True") is True
    assert coerce_bool("False") is False
