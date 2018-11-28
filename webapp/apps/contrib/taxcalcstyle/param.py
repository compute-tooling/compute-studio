from webapp.apps.core.param import CheckBox, BaseParam

class Param(BaseParam):

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
