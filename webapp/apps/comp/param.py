from django import forms

from .fields import (
    ValueField,
    coerce_bool,
    coerce_float,
    coerce_int,
    coerce_date,
    coerce,
)
from .utils import dims_to_dict, dims_to_string


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
                choices_.remove(self.default_value)
                choices_.insert(0, self.default_value)
                choices = [(c, c) for c in choices_]
            else:
                choices = None
        else:
            choices = None
        if isinstance(self.default_value, list):
            self.default_value = ", ".join([str(v) for v in self.default_value])
        if isinstance(self.default_value, bool):
            self.default_value = str(self.default_value)
        attrs = {"placeholder": self.default_value, "class": "model-param"}
        attrs.update(field_kwargs)
        if self.number_dims == 0 and choices is not None:
            attrs["class"] += " unedited"
            self.form_field = forms.TypedChoiceField(
                label=self.label,
                required=False,
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


class CheckBox:
    def __init__(self, name, label, default_value, **field_kwargs):
        self.name = name
        self.label = label
        self.default_value = default_value
        attrs = {"placeholder": str(self.default_value), "class": "model-param"}
        self.form_field = forms.NullBooleanField(
            label=self.label,
            widget=forms.TextInput(attrs=attrs),
            required=False,
            **field_kwargs,
        )


class Param:

    field_class = Value

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
        # title is preferred, but long_name is also acceptable.
        self.title = self.attributes.get("title", None) or self.attributes["long_name"]
        self.description = self.attributes["description"]
        self.number_dims = self.attributes.get("number_dims", 1)
        self.col_fields = []
        self.meta_parameters = meta_parameters
        for mp, value in meta_parameters.items():
            setattr(self, mp, value)
        self.coerce_func = self.get_coerce_func()
        self.default_value = self.attributes["value"]

        self.info = " ".join(
            [attributes["description"], attributes.get("notes") or ""]
        ).strip()

        self.fields = {}
        self.set_fields(self.default_value)

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
        if not value:
            value = [{"value": "disabled"}]
            field_kwargs["disabled"] = True
            coerce_func = str
        else:
            coerce_func = self.coerce_func
        for value_object in value:
            field_name, _ = dims_to_string(
                self.name, value_object, self.meta_parameters
            )
            label = self.format_label(value_object)
            field = self.field_class(
                field_name,
                label,
                value_object["value"],
                coerce_func,
                self.number_dims,
                self.attributes.get("validators", {}),
                **field_kwargs,
            )
            self.fields[field_name] = field.form_field
            self.col_fields.append(field)
        # get attribute indicating whether parameter uses a checkbox.
        self.has_checkbox = "checkbox" in self.attributes
        if self.has_checkbox:
            field_name = f"{self.name}_checkbox"
            # TODO: Projects should use checkbox label instead of "CPI".
            self.checkbox_field = CheckBox(
                field_name, "CPI", self.attributes["checkbox"], **field_kwargs
            )
            self.fields[field_name] = self.checkbox_field.form_field

    def format_label(self, value_object):
        label = []
        for dim_name, dim_value in value_object.items():
            if dim_name != "value" and dim_name not in self.meta_parameters:
                label.append((f"{dim_name.replace('_', ' ').upper()}", dim_value))
        if len(label) == 1:
            # just return the value in this case.
            return label[0][1]
        else:
            return " ".join([f"{name}: {val}" for name, val in label])

    def get_coerce_func(self):
        datatype = self.attributes["type"]
        return self.type_map[datatype]
