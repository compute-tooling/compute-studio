from webapp.apps.core.param import Param

class ParamToolsParam(Param):

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
        for value_item in value:
            suffix = self.name_from_dims(value_item)
            if suffix:
                field_name = f"{self.name}___{suffix}"
            else:
                field_name = self.name
            field = self.field_class(
                field_name,
                suffix,
                value_item["value"],
                self.coerce_func,
                1,
                **field_kwargs
            )
            self.fields[field_name] = field.form_field
            self.col_fields.append(field)

    def name_from_dims(self, value):
        dims = {k: v for k, v in value.items() if k != "value"}
        if dims:
            suffix = "__".join([
                f"{dim_name}_{dim_value}" for dim_name, dim_value in dims.items()
            ])
        else:
            suffix = ""
        return suffix