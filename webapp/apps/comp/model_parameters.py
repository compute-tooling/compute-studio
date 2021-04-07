from typing import Union


import paramtools as pt

from webapp.apps.comp.models import ModelConfig
from webapp.apps.comp.compute import Compute, SyncCompute, JobFailError
from webapp.apps.comp import actions
from webapp.apps.comp.exceptions import AppError, NotReady


import os
import json

INPUTS = os.path.join(os.path.abspath(os.path.dirname(__file__)), "inputs.json")


def pt_factory(classname, defaults):
    return type(classname, (pt.Parameters,), {"defaults": defaults})


class ModelParameters:
    """
    Handles logic for getting cached model parameters and updating the cache.
    """

    def __init__(self, project: "Project", compute: Union[SyncCompute, Compute] = None):
        self.project = project
        print(self.project)
        if compute is not None:
            self.comptue = compute
        elif self.project.cluster.version == "v0":
            self.compute = compute or SyncCompute()
        else:
            self.compute = compute or Compute()

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

    def meta_parameters_parser(self) -> pt.Parameters:
        res = self.get_inputs()
        params = pt_factory("MetaParametersParser", res["meta_parameters"])()
        # params._defer_validation = True
        return params

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

    def cleanup_meta_parameters(self, meta_parameters_values, meta_parameters):
        # clean up meta parameters before saving them.
        if not meta_parameters_values:
            return {}

        mp = pt_factory("MP", meta_parameters)()
        mp.adjust(meta_parameters_values)
        return mp.specification(meta_data=False, serializable=True)

    def get_inputs(self, meta_parameters_values=None):
        """
        Get cached version of inputs or retrieve new version.
        """
        meta_parameters_values = meta_parameters_values or {}

        try:
            self.config = ModelConfig.objects.get(
                project=self.project,
                model_version=str(self.project.latest_tag),
                meta_parameters_values=meta_parameters_values,
            )
            print("STATUS", self.config.status)
            if self.config.status != "SUCCESS":
                print("raise yo")
                raise NotReady(self.config)
        except ModelConfig.DoesNotExist:
            response = self.compute.submit_job(
                project=self.project,
                task_name=actions.INPUTS,
                task_kwargs={"meta_param_dict": meta_parameters_values or {}},
                path_prefix="/api/v1/jobs"
                if self.project.cluster.version == "v1"
                else "",
            )
            if self.project.cluster.version == "v1":
                self.config = ModelConfig.objects.create(
                    project=self.project,
                    model_version=str(self.project.latest_tag),
                    meta_parameters_values=meta_parameters_values,
                    inputs_version="v1",
                    job_id=response,
                    status="PENDING",
                )
                raise NotReady(self.config)

            success, result = response
            if not success:
                raise AppError(meta_parameters_values, result["traceback"])

            save_vals = self.cleanup_meta_parameters(
                meta_parameters_values, result["meta_parameters"]
            )

            self.config = ModelConfig.objects.create(
                project=self.project,
                model_version=str(self.project.latest_tag),
                meta_parameters_values=save_vals,
                meta_parameters=result["meta_parameters"],
                model_parameters=result["model_parameters"],
                inputs_version="v1",
            )

        return {
            "meta_parameters": self.config.meta_parameters,
            "model_parameters": self.config.model_parameters,
        }
