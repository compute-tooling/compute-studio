import paramtools as pt

from webapp.apps.comp.models import ModelConfig
from webapp.apps.comp.compute import SyncCompute, JobFailError
from webapp.apps.comp import actions
from webapp.apps.comp.exceptions import AppError


import os
import json

INPUTS = os.path.join(os.path.abspath(os.path.dirname(__file__)), "inputs.json")


def pt_factory(classname, defaults):
    return type(classname, (pt.Parameters,), {"defaults": defaults})


class ModelParameters:
    """
    Handles logic for getting cached model parameters and updating the cache.
    """

    def __init__(self, project: "Project", compute: SyncCompute = None):
        self.project = project
        self.compute = compute or SyncCompute()
        self.config = None

    def defaults(self, init_meta_parameters=None):
        # get Parameters class for meta parameters and adjust its values.
        meta_param_parser = self.meta_parameters_parser()
        meta_param_parser.adjust(init_meta_parameters or {})
        meta_parameters = meta_param_parser.dump()
        return {
            "model_parameters": self.model_parameters_parser(
                meta_param_parser.specification(meta_data=False, serializable=True)
            ),
            "meta_parameters": meta_parameters,
        }

    def meta_parameters_parser(self):
        res = self.get_inputs()
        return pt_factory("MetaParametersParser", res["meta_parameters"])()

    def model_parameters_parser(self, meta_parameters_values=None):
        res = self.get_inputs(meta_parameters_values)
        # TODO: just return defaults or return the parsers, too?
        # model_parameters_parser = {}
        # for sect, defaults in res["model_parameters"]:
        #     model_parameters_parser[sect] = type(
        #         "Parser", (pt.Parameters), {"defaults": defaults},
        #     )()
        # return model_parameters_parser
        return res["model_parameters"]

    def get_inputs(self, meta_parameters_values=None):
        """
        Get cached version of inputs or retrieve new version.
        """
        meta_parameters_values = meta_parameters_values or {}

        try:
            config = ModelConfig.objects.get(
                project=self.project,
                model_version=self.project.version,
                meta_parameters_values=meta_parameters_values,
            )
        except ModelConfig.DoesNotExist:
            success, result = self.compute.submit_job(
                project=self.project,
                task_name=actions.INPUTS,
                task_kwargs={"meta_param_dict": meta_parameters_values or {}},
            )
            if not success:
                raise AppError(meta_parameters_values, result["traceback"])

            # clean up meta parameters before saving them.
            if meta_parameters_values:
                mp = pt_factory("MP", result["meta_parameters"])()
                mp.adjust(meta_parameters_values)
                save_vals = mp.specification(meta_data=False, serializable=True)
            else:
                save_vals = {}

            config = ModelConfig.objects.create(
                project=self.project,
                model_version=self.project.version,
                meta_parameters_values=save_vals,
                meta_parameters=result["meta_parameters"],
                model_parameters=result["model_parameters"],
                inputs_version="v1",
            )

        self.config = config
        return {
            "meta_parameters": config.meta_parameters,
            "model_parameters": config.model_parameters,
        }
