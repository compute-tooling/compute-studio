from django import forms

from .utils import is_reverse, is_wildcard

class SeparatedValueField(forms.Field):

    def __init__(self, *, coerce=lambda val: val, empty_value="", **kwargs):
        self.coerce = coerce
        self.empty_value = empty_value
        super().__init__(**kwargs)

    def clean(self, value):
        value = super().clean(value)
        return value

    def _coerce(self, value):
        if value == self.empty_value or value in self.empty_values:
            return self.empty_value
        try:
            value = self.coerce(value)
        except (ValueError, TypeError):
            raise ValidationError(self.error_messages['invalid'], code='invalid')
        return value

    def to_python(self, value):
        if not value:
            return value
        raw_values = value.split(',')
        python_values = []
        for raw_value in raw_values:
            stripped = raw_value.strip()
            if is_reverse(stripped) or is_wildcard(stripped):
                python_values.append(stripped)
            else:
                python_values.append(self._coerce(stripped))
        return python_values
