from webapp.apps.comp.compute import SyncCompute, JobFailError
from webapp.apps.comp import actions
from webapp.apps.comp.exceptions import AppError
from webapp.apps.comp.meta_parameters import translate_to_django


class Displayer:
    def __init__(self, project, Param, **meta_parameters):
        self.project = project
        self.Param = Param
        self.meta_parameters = meta_parameters
        self._cache = {}

    def defaults(self, flat=True, use_param_cls=True):
        if flat:
            return self._default_flatdict(use_param_cls=use_param_cls)
        else:
            return self._default_form()

    def parsed_meta_parameters(self):
        meta_parameters, _ = self.package_defaults()
        return translate_to_django(meta_parameters)

    def package_defaults(self, cache_result=True):
        """
        Get the package defaults from the upstream project. Currently, this is
        done by importing the project and calling a function or series of
        functions to load the project's inputs data. In the future, this will
        be done over the distributed REST API.
        """
        args = tuple(v for k, v in sorted(self.meta_parameters.items()))
        if args in self._cache:
            res = self._cache[args]
            return res["meta_parameters"], res["model_parameters"]
        success, result = SyncCompute().submit_job(
            {"meta_param_dict": self.meta_parameters},
            self.project.worker_ext(action=actions.INPUTS),
        )
        if not success:
            raise AppError(self.meta_parameters, result)
        if cache_result:
            self._cache[args] = {
                "meta_parameters": result[0],
                "model_parameters": result[1],
            }
        return result

    def _default_flatdict(self, use_param_cls=True):
        """
        Get _flat_ dictionary of default parameters, i.e. major section types
        are collapsed. This is used to specify the default inputs on the Django
        Form and for looking up parameter data. Return parameters after
        wrapping in the specified `Param`.
        """
        _, raw_defaults = self.package_defaults()
        default_params = {}
        for defaults in raw_defaults.values():
            for k, v in defaults.items():
                if use_param_cls:
                    param = self.Param(k, v, **self.meta_parameters)
                    default_params[param.name] = param
                else:
                    default_params[k] = v
        return default_params

    def _default_form(self):
        """
        Get dictionary split by major input types. Each parameter is wrapped
        in the specified `Param`. This is used to build the GUI.
        """
        _, raw_defaults = self.package_defaults()
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
            section_name = y.get("section_1", " ")
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
                section_name = z.get("section_2", " ")
                new_param = {y: self.Param(y, z, **self.meta_parameters)}
                section = next((item for item in output if section_name in item), None)
                if not section:
                    output.append({section_name: [new_param]})
                else:
                    section[section_name].append(new_param)
        return output + free_fields
