from django import forms

from webapp.apps.comp.param import Param, Value
from webapp.apps.comp.fields import ValueField, SeparatedValueField
from .utils import dims_to_string


class Value:
    def __init__(
        self,
        name,
        label,
        default_value,
        coerce_func,
        number_dims,
        validators,
        **field_kwargs,
    ):
        self.name = name
        self.label = label
        self.default_value = default_value
        self.number_dims = number_dims
        if self.number_dims == 0 and "choice" in validators:
            choices_ = validators["choice"]["choices"]
            if len(choices_) < 25:
                dv_ix = choices_.remove(self.default_value)
                choices_.insert(0, self.default_value)
                choices = [(c, c) for c in choices_]
            else:
                choices = None
        else:
            choices = None
        if isinstance(self.default_value, list):
            self.default_value = ", ".join([str(v) for v in self.default_value])
        attrs = {"placeholder": self.default_value}
        if self.number_dims == 0:
            if choices is not None:
                attrs["class"] = "unedited"
                self.form_field = forms.TypedChoiceField(
                    label=self.label,
                    required=False,
                    initial=self.default_value,
                    widget=forms.Select(attrs=attrs),
                    coerce=coerce_func,
                    choices=choices,
                    **field_kwargs,
                )
            else:
                self.form_field = ValueField(
                    label=self.label,
                    widget=forms.TextInput(attrs=attrs),
                    required=False,
                    coerce=coerce_func,
                    number_dims=number_dims,
                    **field_kwargs,
                )
        else:
            self.form_field = SeparatedValueField(
                label=self.label,
                widget=forms.TextInput(attrs=attrs),
                required=False,
                coerce=coerce_func,
                number_dims=number_dims,
                **field_kwargs,
            )


class ParamToolsParam(Param):
    field_class = Value

    def set_fields(self, value, **field_kwargs):
        """
        Value is of the shape:
            [
                {"value": val, "dim0": dimvalue, ...},
                {"value": val, "dim0": otherdimvalue, ...},
            ]

        Create a parameter for all value items in list such that:
        -

        """
        for value_object in value:
            field_name, suffix = dims_to_string(
                self.name, value_object, self.meta_parameters
            )
            label = self.format_label(value_object)
            field = self.field_class(
                field_name,
                label,
                value_object["value"],
                self.coerce_func,
                self.number_dims,
                self.attributes.get("validators", {}),
                **field_kwargs,
            )
            self.fields[field_name] = field.form_field
            self.col_fields.append(field)

    def format_label(self, value_object):
        label = ""
        for dim_name, dim_value in value_object.items():
            if dim_name != "value" and dim_name not in self.meta_parameters:
                label += f"{dim_name.replace('_', ' ').title()}: {dim_value} "
        return label
