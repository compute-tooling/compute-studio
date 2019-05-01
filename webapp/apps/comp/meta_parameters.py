from dataclasses import dataclass, field
from typing import List
from django import forms

from marshmallow import Schema, fields, validate, exceptions
from paramtools import ValueValidatorSchema

from webapp.apps.comp.fields import coerce_bool


@dataclass
class MetaParameters:
    parameters: List["MetaParameter"] = field(default_factory=list)

    def validate(self, fields):
        validated = {}
        if not self.parameters:
            return validated
        for param in self.parameters:
            try:
                cleaned = param.field.clean(fields.get(param.name))
            except (forms.ValidationError, KeyError) as e:
                # fall back on default. deal with bad data in full validation.
                cleaned = param.field.clean(param.default)
            validated[param.name] = cleaned
        return validated


@dataclass
class MetaParameter:
    name: str
    title: str
    default: str
    field: forms.Field


def translate_to_django(meta_parameters):
    new_mp = {}
    for name, data in meta_parameters["meta_parameters"].items():
        if data["type"] == "str" and "choice" in data["validators"]:
            field = forms.ChoiceField(
                choices=[(c, c) for c in data["validators"]["choice"]["choices"]]
            )
        elif data["type"] == "str":
            field = forms.CharField()
        elif data["type"] in ("int", "float"):
            field = forms.IntegerField if data["type"] == "int" else forms.FloatField
            if "range" in data["validators"]:
                min_value = data["validators"]["range"]["min"]
                max_value = data["validators"]["range"]["max"]
                field = field(min_value=min_value, max_value=max_value)
            else:
                field = field()
        else:  # bool
            field = forms.TypedChoiceField(
                coerce=coerce_bool, choices=list((i, i) for i in (True, False))
            )
        new_mp[name] = dict(data, **{"djangofield": field})
    return new_mp
