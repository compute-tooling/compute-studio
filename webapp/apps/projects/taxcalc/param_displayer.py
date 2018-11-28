from taxcalc.tbi import get_defaults as taxcalc_pckg_defaults


from webapp.apps.core import param_displayer
from webapp.apps.contrib.taxcalcstyle.param import Param


class ParamDisplayer(param_displayer.ParamDisplayer):
    ParamCls = Param

    def package_defaults(self):
        return taxcalc_pckg_defaults(**self.meta_parameters)