from webapp.apps.core.displayer import Displayer
from webapp.apps.core.param import Param


class {Project}Displayer(Displayer):
    param_class = Param

    def package_defaults(self):
        """
        Get the package defaults from the upstream project. Currently, this is
        done by importing the project and calling a function or series of
        functions to load the project's inputs data. In the future, this will
        be done over the distributed REST API.
        """
        pass