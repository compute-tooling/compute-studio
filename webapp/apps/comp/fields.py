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

    def __init__(
        self, *, coerce=lambda val: val, number_dims=1, empty_value="", **kwargs
    ):
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
        python_value = []
        value = value.strip()
        python_value = self._coerce(value)
        return python_value


class SeparatedValueField(ValueField):
    def to_python(self, value):
        if not value:
            return value
        raw_values = value.split(",")
        python_values = []
        for raw_value in raw_values:
            stripped = raw_value.strip()
            if is_reverse(stripped) or is_wildcard(stripped):
                python_values.append(stripped)
            else:
                python_values.append(self._coerce(stripped))
        if self.number_dims == 0:
            if len(python_values) > 1:
                raise forms.ValidationError(
                    self.error_messages["invalid_type"], code="invalid"
                )
            else:
                python_values = python_values[0]
        return python_values
