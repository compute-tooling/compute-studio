from dataclasses import dataclass, field
from typing import List
from django import forms


@dataclass
class MetaParameters:
    parameters: List['MetaParameter'] = field(default_factory=list)


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
    default: str
    field: forms.Field


meta_parameters = MetaParameters()