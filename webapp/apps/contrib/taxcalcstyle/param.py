from webapp.apps.core.param import CheckBox, BaseParam
from webapp.apps.core.fields import coerce_bool, coerce_float, coerce_int

class TaxcalcStyleParam(BaseParam):

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
        self.info = " ".join([
            attributes['description'],
            attributes.get('irs_ref') or "",
            attributes.get('notes') or ""
        ]).strip()
        field_kwargs = {"disabled": self.gray_out}
        self.set_fields(self.default_value, **field_kwargs)

    def set_fields(self, value, **field_kwargs):
        # some lists are 2-D even though they only represent one year.
        if isinstance(value[0], list):
            value = value[0]
        for dim1 in range(len(value)):
            if len(value) > 1:
                field_name = f"{self.name}_{dim1}"
            else:
                field_name = self.name
            field = self.field_class(
                field_name,
                self.attributes["col_label"][dim1],
                value[dim1],
                self.coerce_func,
                **field_kwargs
            )
            self.fields[field_name] = field.form_field
            self.col_fields.append(field)

        # get attribute indicating whether parameter is cpi inflatable.
        self.inflatable = self.attributes.get("cpi_inflatable", False)
        if self.inflatable:
            field_name = f"{self.name}_cpi"
            self.cpi_field = CheckBox(
                field_name,
                "CPI",
                self.attributes['cpi_inflated'],
                **field_kwargs)
            self.fields[field_name] = self.cpi_field.form_field

    def get_coerce_func(self):
        if self.attributes["boolean_value"]:
            coerce_func = coerce_bool
        elif self.attributes["integer_value"]:
            coerce_func = coerce_int
        else:
            coerce_func = coerce_float
        return coerce_func
