from webapp.apps.core.param import Param, Value
from .utils import dims_to_string


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
