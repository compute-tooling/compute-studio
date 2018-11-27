from django import forms

from webapp.apps.projects.taxcalc.fields import SeparatedValueField


class SeparatedValue:

    def __init__(self, name, label, default_value, coerce_func, **field_kwargs):
        self.name = name
        self.label = label
        attrs = {
            'class': 'form-control',
            'placeholder': default_value,
        }
        self.form_field = SeparatedValueField(
            label=self.label,
            widget=forms.TextInput(attrs=attrs),
            required=False,
            coerce=coerce_func,
            **field_kwargs
        )


class CheckBox:

    def __init__(self, name, label, default_value, **field_kwargs):
        self.name = name
        self.label = label
        attrs = {
            'class': 'form-control sr-only',
        }
        self.form_field = forms.BooleanField(
            label=self.label,
            widget=forms.TextInput(attrs=attrs),
            required=False,
            initial=default_value,
            **field_kwargs
        )


class BaseParam:

    FieldCls = SeparatedValue

    def __init__(self, name, attributes, **meta_parameters):
        self.name = name
        self.attributes = attributes
        self.long_name = self.attributes["long_name"]
        self.description = self.attributes["description"]
        self.col_fields = []
        for mp, value in meta_parameters.items():
            setattr(self, mp, value)

        # TODO: swap to use "type" attribute instead of process of elimination
        if self.attributes["boolean_value"]:
            self.coerce_func = lambda x: bool(x)
        elif self.attributes["integer_value"]:
            self.coerce_func = lambda x: int(x)
        else:
            self.coerce_func = lambda x: float(x)

        self.default_value = self.attributes["value"]

        self.fields = {}

    def set_fields(self, values, **field_kwargs):
        for value in values:
            # TODO: find better way to map suffixes to parameters based on
            # their dimensions
            suffix_ix = "_".join(suff[0] for k, suff in value.items() if k != "value")
            suffix_name = "_".join(suff[1] for k, suff in value.items() if k != "value")
            if suffix_ix:
                field_name = f"{self.name}_{suffix_ix}"
            else:
                field_name = self.name
            field = self.FieldCls(
                field_name,
                suffix_name,
                value["value"],
                self.coerce_func,
                **field_kwargs
            )
            self.fields[field_name] = field.form_field
            self.col_fields.append(field)


class Param(BaseParam):

    def __init__(self, name, attributes, **meta_parameters):
        super().__init__(self, name, attributes, **meta_parameters)
        self.set_fields(self.default_value)


