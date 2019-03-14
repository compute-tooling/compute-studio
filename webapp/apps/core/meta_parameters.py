from dataclasses import dataclass, field
from typing import List
from django import forms

from marshmallow import Schema, fields, validate, exceptions
from paramtools import ValueValidatorSchema

from webapp.apps.core.fields import coerce_bool


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


class MetaParameterSchema(Schema):
    title = fields.Str()
    default = fields.Field()
    _type = fields.Str(
        required=True,
        validate=validate.OneOf(choices=["str", "float", "int", "bool"]),
        attribute="type",
        data_key="type",
    )
    validators = fields.Nested(ValueValidatorSchema(), required=True)


class MetaParametersSchema(Schema):
    meta_parameters = fields.Dict(
        keys=fields.Str(), values=fields.Nested(MetaParameterSchema)
    )


def translate_to_django(meta_parameters):
    mpschema = MetaParametersSchema()
    mpschema.load(meta_parameters)
    parameters = []
    for name, data in meta_parameters["meta_parameters"].items():
        if data["type"] == "str" and "choice" in data["validators"]:
            field = forms.ChoiceField(choices=data["validators"]["choices"])
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
        parameters.append(
            MetaParameter(
                name=name, title=data["title"], field=field, default=data["default"]
            )
        )
    return MetaParameters(parameters=parameters)
