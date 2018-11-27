from django import forms

from webapp.apps.taxcalc.fields import SeparatedValueField


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


class TaxCalcParam(BaseParam):

    def __init__(self, name, attributes, **meta_parameters):
        super().__init__(name, attributes, **meta_parameters)
        if "compatible_data" in attributes:
            self.gray_out = not (
                (attributes["compatible_data"]["cps"] and
                 self.data_source == "CPS")
                or (attributes["compatible_data"]["puf"] and
                    self.data_source == "PUF"))
        else:
            # if compatible_data is not specified do not gray out
            self.gray_out = False
        field_kwargs = {"disabled": self.gray_out}
        dictvalues = self.convert_to_dict(self.default_value)
        self.set_fields(dictvalues, **field_kwargs)

    def convert_to_dict(self, value):
        values = []
        if isinstance(value[0], list):
            for year in range(len(value)):
                for dim1 in range(len(value[0])):
                    values.append({
                        self.attributes["col_var"]: (str(dim1), self.attributes["col_label"][dim1]),
                        "value": value[year][dim1]})
        else:
            for year in range(len(value)):
                values.append({"value": value[year]})
        return values

    def set_fields(self, values, **field_kwargs):
        super().set_fields(values, **field_kwargs)
        # get attribute indicating whether parameter is cpi inflatable.
        self.inflatable = self.attributes.get("cpi_inflatable", False)
        if self.inflatable:
            name = f"{self.name}_cpi"
            self.cpi_field = CheckBox(
                name,
                "CPI",
                self.attributes['cpi_inflated'],
                **field_kwargs)
            self.fields[name] = self.cpi_field.form_field
