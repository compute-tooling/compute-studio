import datetime

from django import forms
from django.utils.translation import gettext_lazy as _

from .utils import is_reverse, is_wildcard


def coerce_int(val):
    return int(float(val))


def coerce_float(val):
    return float(val)


def coerce_bool(val):
    return val in ("True", True)


def coerce(val):
    return val


def coerce_date(val):
    # see django.DateField and Django BaseTemporalField de-serializers
    input_formats = ["%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"]
    if val in ["", None]:
        return None
    if isinstance(val, datetime.datetime):
        return val.date()
    if isinstance(val, datetime.date):
        return val
    for format in input_formats:
        try:
            # just want to make sure that it is serializable
            res = datetime.datetime.strptime(val, format).date()
            return res.strftime(format)
        except (ValueError, TypeError):
            continue
    raise ValueError("Invalid date supplied")


class ValueField(forms.Field):
    default_error_messages = {
        "invalid_type": _("%(value)s is not able to be converted to the correct type")
    }

    def __init__(self, coerce=lambda val: val, number_dims=1, empty_value="", **kwargs):
        self.coerce = coerce
        self.empty_value = empty_value
        self.number_dims = number_dims
        super().__init__(**kwargs)

    def clean(self, value):
        value = super().clean(value)
        return value

    def _coerce(self, value):
        if value == self.empty_value or value in self.empty_values:
            return self.empty_value
        try:
            value = self.coerce(value)
        except (ValueError, TypeError) as e:
            raise forms.ValidationError(
                self.error_messages["invalid_type"],
                params={"value": value},
                code="invalid",
            )
        return value

    def to_python(self, value):
        if not value:
            return value
        raw_values = value.split(",")
        python_values = []
        num_ops = 0
        for raw_value in raw_values:
            stripped = raw_value.strip()
            if is_reverse(stripped) or is_wildcard(stripped):
                python_values.append(stripped)
                num_ops += 1
            else:
                python_values.append(self._coerce(stripped))
        # Some projects like Tax-Brain extend their parameters
        # along some dimension. For those projects, the entire
        # list is kept even though it should just be a single
        # value.
        if self.number_dims == 0 and len(python_values) == 1 and num_ops == 0:
            python_values = python_values[0]
        return python_values


class DataList(forms.Widget):
    def __init__(self, data_list, placeholder, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_list = data_list
        self.placeholder = placeholder

    def render(self, name, value, attrs=None, renderer=None):
        attrs = self.build_attrs(self.attrs, attrs)
        option_str = "\n".join(
            [f'<option value="{value[0]}">' for value in self.data_list]
        )
        class_ = attrs.get("class", "")
        class_str = f'class="{class_}"' if class_ else ""
        value_str = value if value is not None else ""
        return f"""
            <input 
                list="id_{name}-list" 
                id="id_{name}" 
                name="{name}" 
                {class_str} 
                placeholder="{self.placeholder}" 
                value="{value_str}"
            />
            <datalist id="id_{name}-list"> {option_str} </datalist>
            """


class ChoiceValueField(ValueField):
    default_error_messages = {
        "invalid_type": _("%(value)s is not able to be converted to the correct type"),
        "invalid_choice": _(
            "Select a valid choice. %(value)s is not one of the available choices."
        ),
    }

    def __init__(
        self, choices, coerce=lambda val: val, number_dims=1, empty_value="", **kwargs
    ):
        super().__init__(coerce, number_dims, empty_value, **kwargs)
        self.choices = choices

    def validate(self, value):
        super().validate(value)
        if not self.valid_value(value):
            print("fail", value)
            raise forms.ValidationError(
                self.error_messages["invalid_choice"],
                code="invalid_choice",
                params={"value": value},
            )

    def valid_value(self, value):
        if not isinstance(value, list):
            values = [value]
        else:
            values = value
        for v in values:
            if is_wildcard(v) or is_reverse(v) or v in (self.empty_value, None):
                continue
            elif (v, v) not in self.choices:
                return False
        return True
