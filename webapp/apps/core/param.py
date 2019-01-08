from django import forms

from .fields import (SeparatedValueField, coerce_bool,
                     coerce_float, coerce_int, coerce_date, coerce)


class SeparatedValue:

    def __init__(self, name, label, default_value, coerce_func, number_dims,
                 **field_kwargs):
        self.name = name
        self.label = label
        self.default_value = default_value
        if isinstance(self.default_value, list):
            self.default_value = ', '.join([str(v) for v in self.default_value])
        attrs = {
            'class': 'form-control',
            'placeholder': self.default_value,
        }
        self.form_field = SeparatedValueField(
            label=self.label,
            widget=forms.TextInput(attrs=attrs),
            required=False,
            coerce=coerce_func,
            number_dims=number_dims,
            **field_kwargs
        )


class CheckBox:

    def __init__(self, name, label, default_value, **field_kwargs):
        self.name = name
        self.label = label
        self.default_value = default_value
        attrs = {
            'placeholder': str(self.default_value),
        }
        self.form_field = forms.NullBooleanField(
            label=self.label,
            widget=forms.TextInput(attrs=attrs),
            required=False,
            **field_kwargs
        )


class BaseParam:

    field_class = SeparatedValue

    type_map = {
        "int": coerce_int,
        "float": coerce_float,
        "bool": coerce_bool,
        "date": coerce_date,
        "str": coerce,
    }

    def __init__(self, name, attributes, **meta_parameters):
        self.name = name
        self.attributes = attributes
        self.long_name = self.attributes["long_name"]
        self.description = self.attributes["description"]
        self.number_dims = self.attributes.get("number_dims", 1)
        self.col_fields = []
        for mp, value in meta_parameters.items():
            setattr(self, mp, value)
        self.coerce_func = self.get_coerce_func()
        self.default_value = self.attributes["value"]

        self.info = " ".join([
            attributes['description'],
            attributes.get('notes') or ""
        ]).strip()

        self.fields = {}

    def set_fields(self, value, **field_kwargs):
        field = self.field_class(
            self.name,
            '',
            value,
            self.coerce_func,
            self.number_dims,
            **field_kwargs
        )
        self.fields[self.name] = field.form_field
        self.col_fields.append(field)

    def get_coerce_func(self):
        datatype = self.attributes["type"]
        return self.type_map[datatype]


class Param(BaseParam):

    def __init__(self, name, attributes, **meta_parameters):
        super().__init__(name, attributes, **meta_parameters)
        self.set_fields(self.default_value)
