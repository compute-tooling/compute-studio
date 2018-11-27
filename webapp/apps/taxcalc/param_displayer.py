from taxcalc.tbi import get_defaults as taxcalc_pckg_defaults

from .param import TaxCalcParam as Param


class ParamDisplayer:

    ParamCls = Param

    def __init__(self, **meta_parameters):
        self.meta_parameters = meta_parameters

    def get_defaults(self, flat=False):
        """
        Get _flat_ dictionary of default parameters, i.e. major section types
        are collapsed. This is used to specify the default inputs on the Django
        Form. Return parameters after wrapping in the
        specified `ParamCls`.
        """
        raw_defaults = self.package_defaults()
        default_params = {}
        for input_type, defaults in raw_defaults.items():
            for k, v in defaults.items():
                param = self.ParamCls(k, v, **self.meta_parameters)
                default_params[param.name] = param
        return default_params

    def default_form(self):
        """
        Get dictionary split by major input types. Each parameter is wrapped
        in the specified `ParamCls`. This is used to build the GUI.
        """
        raw_defaults = self.package_defaults()
        major_groups = {}
        for input_type, defaults in raw_defaults.items():
            groups = self._parse_top_level(defaults)
            for x in groups:
                for y, z in x.items():
                    x[y] = self._parse_sub_category(z)
            major_groups[input_type] = groups
        return major_groups

    def package_defaults(self):
        return taxcalc_pckg_defaults(**self.meta_parameters)

    def _parse_top_level(self, ordered_dict):
        output = []
        for x, y in ordered_dict.items():
            section_name = dict(y).get("section_1")
            if section_name:
                section = next(
                    (item for item in output if section_name in item), None
                )
                if not section:
                    output.append({section_name: [{x: dict(y)}]})
                else:
                    section[section_name].append({x: dict(y)})
        return output

    def _parse_sub_category(self, field_section):
        output = []
        free_fields = []
        for x in field_section:
            for y, z in x.items():
                section_name = dict(z).get("section_2")
                new_param = {
                    y[y.index("_") + 1 :]: self.ParamCls(
                        y, z, **self.meta_parameters
                    )
                }
                if section_name:
                    section = next(
                        (item for item in output if section_name in item), None
                    )
                    if not section:
                        output.append({section_name: [new_param]})
                    else:
                        section[section_name].append(new_param)
                else:
                    # can remove?
                    raise ValueError()
                    # free_fields.append(
                    #     field_section.pop(field_section.index(x))
                    # )
                    # free_fields[free_fields.index(x)] = new_param
        return output + free_fields
