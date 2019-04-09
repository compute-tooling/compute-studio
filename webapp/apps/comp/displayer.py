from webapp.apps.comp.compute import SyncCompute, JobFailError
from webapp.apps.comp import actions


class Displayer:
    def __init__(self, project, ioclasses, **meta_parameters):
        self.project = project
        self.ioclasses = ioclasses
        self.meta_parameters = meta_parameters

    def defaults(self, flat=True):
        if flat:
            return self._default_flatdict()
        else:
            return self._default_form()

    def package_defaults(self):
        """
        Get the package defaults from the upstream project. Currently, this is
        done by importing the project and calling a function or series of
        functions to load the project's inputs data. In the future, this will
        be done over the distributed REST API.
        """
        _, result = SyncCompute().submit_job(
            self.meta_parameters, self.project.worker_ext(action=actions.INPUTS)
        )
        return result

    def _default_flatdict(self):
        """
        Get _flat_ dictionary of default parameters, i.e. major section types
        are collapsed. This is used to specify the default inputs on the Django
        Form and for looking up parameter data. Return parameters after
        wrapping in the specified `ioclasses.Param`.
        """
        raw_defaults = self.package_defaults()
        default_params = {}
        for inputs_style, defaults in raw_defaults.items():
            for k, v in defaults.items():
                param = self.ioclasses.Param(k, v, **self.meta_parameters)
                default_params[param.name] = param
        return default_params

    def _default_form(self):
        """
        Get dictionary split by major input types. Each parameter is wrapped
        in the specified `ioclasses.Param`. This is used to build the GUI.
        """
        raw_defaults = self.package_defaults()
        major_groups = {}
        for inputs_style, defaults in raw_defaults.items():
            groups = self._parse_top_level(defaults)
            for x in groups:
                for y, z in x.items():
                    x[y] = self._parse_sub_category(z)
            major_groups[inputs_style] = groups
        return major_groups

    def _parse_top_level(self, ordered_dict):
        output = []
        for x, y in ordered_dict.items():
            section_name = y.get("section_1")
            if section_name:
                section = next((item for item in output if section_name in item), None)
                if not section:
                    output.append({section_name: [{x: y}]})
                else:
                    section[section_name].append({x: y})
        return output

    def _parse_sub_category(self, field_section):
        output = []
        free_fields = []
        for x in field_section:
            for y, z in x.items():
                section_name = z.get("section_2")
                new_param = {y: self.ioclasses.Param(y, z, **self.meta_parameters)}
                section = next((item for item in output if section_name in item), None)
                if not section:
                    output.append({section_name: [new_param]})
                else:
                    section[section_name].append(new_param)
        return output + free_fields
