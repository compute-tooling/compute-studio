import paramtools as pt

from webapp.apps.comp.compute import SyncCompute, JobFailError
from webapp.apps.comp import actions
from webapp.apps.comp.exceptions import AppError


import os
import json

INPUTS = os.path.join(os.path.abspath(os.path.dirname(__file__)), "inputs.json")


class ModelParameters:
    def __init__(self, project, compute: SyncCompute = None, **init_meta_parameters):
        self.project = project
        self.compute = compute or SyncCompute()

    def defaults(self, init_meta_parameters=None):
        # get Parameters class for meta parameters and adjust its values.
        meta_param_parser = self.meta_parameters_parser()
        meta_param_parser.adjust(init_meta_parameters or {})

        # TODO: should we load each sect into a parameters class or just pass
        # the data along?
        # get Parameters class for each section's parameters and dump values.
        # model_parameters_parser = self.model_parameters_parser(
        #     meta_param_parser.items()
        # )
        # model_parameters = {
        #     sect: params.dump() for sect, params in model_parameters_parser
        # }
        meta_parameters = meta_param_parser.dump()
        return {
            "model_parameters": self.model_parameters_parser(
                dict(
                    meta_param_parser.specification(meta_data=False, serializable=True)
                )
            ),
            "meta_parameters": meta_parameters,
        }

    def meta_parameters_parser(self):
        res = self.get_inputs()
        MetaParametersParser = type(
            "MetaParametersParser",
            (pt.Parameters,),
            {"defaults": res["meta_parameters"]},
        )
        return MetaParametersParser()

    def model_parameters_parser(self, meta_parameters=None):
        res = self.get_inputs(meta_parameters)
        # model_parameters_parser = {}
        # for sect, defaults in res["model_parameters"]:
        #     model_parameters_parser[sect] = type(
        #         "Parser", (pt.Parameters), {"defaults": defaults},
        #     )()
        return res["model_parameters"]

    def get_inputs(self, meta_parameters=None):
        meta_parameters = meta_parameters or {}
        success, result = self.compute.submit_job(
            {"meta_param_dict": meta_parameters},
            self.project.worker_ext(action=actions.INPUTS),
        )
        if not success:
            raise AppError(meta_parameters, result["traceback"])

        return result
