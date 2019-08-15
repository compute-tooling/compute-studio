from webapp.apps.comp.compute import SyncCompute, JobFailError
from webapp.apps.comp import actions
from webapp.apps.comp.exceptions import AppError
from webapp.apps.comp.meta_parameters import translate_to_django


import os
import json

INPUTS = os.path.join(os.path.abspath(os.path.dirname(__file__)), "inputs.json")


class Displayer:
    def __init__(self, project, compute: SyncCompute = None, **meta_parameters):
        self.project = project
        self.meta_parameters = meta_parameters
        self.compute = compute or SyncCompute()
        self._cache = {}

    def parsed_meta_parameters(self):
        res = self.package_defaults()
        return translate_to_django(res["meta_parameters"])

    def package_defaults(self, cache_result=True):
        """
        Get the package defaults from the upstream project. Currently, this is
        done by importing the project and calling a function or series of
        functions to load the project's inputs data. In the future, this will
        be done over the distributed REST API.
        """
        args = tuple(v for k, v in sorted(self.meta_parameters.items()))
        if args in self._cache:
            return self._cache[args]
        success, result = self.compute.submit_job(
            {"meta_param_dict": self.meta_parameters},
            self.project.worker_ext(action=actions.INPUTS),
        )
        if not success:
            raise AppError(self.meta_parameters, result["traceback"])
        if cache_result:
            self._cache[args] = result
        return result
