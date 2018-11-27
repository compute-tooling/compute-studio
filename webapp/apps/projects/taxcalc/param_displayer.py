from taxcalc.tbi import get_defaults as taxcalc_pckg_defaults


from webapp.apps.core import param_displayer
from .param import TaxCalcParam


class TaxcalcParamDisplayer(param_displayer.ParamDisplayer):
    ParamCls = TaxCalcParam

    def package_defaults(self):
        return taxcalc_pckg_defaults(**self.meta_parameters)