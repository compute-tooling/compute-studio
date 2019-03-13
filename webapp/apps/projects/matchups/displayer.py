from webapp.apps.core.compute import SyncCompute
from webapp.apps.core import actions
from webapp.apps.users.models import Project
from webapp.apps.core.displayer import Displayer
from webapp.apps.contrib.ptstyle.param import ParamToolsParam


class MatchupsDisplayer(Displayer):
    project = Project.objects.get(app_name="matchups")
    param_class = ParamToolsParam

    def package_defaults(self):
        """
        Get the package defaults from the upstream project. Currently, this is
        done by importing the project and calling a function or series of
        functions to load the project's inputs data. In the future, this will
        be done over the distributed REST API.
        """
        return SyncCompute().submit_job(
            self.meta_parameters, self.project.worker_ext(action=actions.INPUTS)
        )
