from webapp.apps.core.param import Param, Value, SeparatedValue
from .utils import to_string, to_dict


class ParamToolsValueMixin:

    def format_label(self):
        _, value_object = to_dict(self.name)
        return ",".join([f"{dim_name.replace('_', ' ').title()}: {dim_value}"
                         for dim_name, dim_value in value_object.items()])


class ParamToolsValue(ParamToolsValueMixin, Value):
    pass


class ParamToolsSeparatedValue(ParamToolsValueMixin, SeparatedValue):
    pass


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
        if self.number_dims == 0:
            self.field_class = ParamToolsValue
        else:
            self.field_class = ParamToolsSeparatedValue

        for value_object in value:
            field_name, suffix = to_string(self.name, value_object)
            field = self.field_class(
                field_name,
                suffix,
                value_object["value"],
                self.coerce_func,
                1,
                **field_kwargs
            )
            self.fields[field_name] = field.form_field
            self.col_fields.append(field)
