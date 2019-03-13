from webapp.apps.core.compute import SyncCompute
from webapp.apps.core import actions
from webapp.apps.users.models import Project
from webapp.apps.contrib.ptstyle.parser import ParamToolsParser
from .displayer import MatchupsDisplayer


class MatchupsParser(ParamToolsParser):
    """
    Formats the parameters into the format defined by the upstream project,
    calls the upstream project's validation functions, and formats the errors
    if they exist.
    """

    project = Project.objects.get(app_name="matchups")
    displayer_class = MatchupsDisplayer

    def parse_parameters(self):
        params, jsonparams, errors_warnings = super().parse_parameters()
        data = {
            "params": params,
            "jsonparams": jsonparams,
            "errors_warnings": errors_warnings,
            **self.valid_meta_params,
        }
        return SyncCompute().submit_job(
            data, self.project.worker_ext(action=actions.PARSE)
        )
