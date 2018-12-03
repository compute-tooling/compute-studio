from taxcalc.tbi import get_defaults as taxcalc_pckg_defaults


from webapp.apps.core.displayer import Displayer
from webapp.apps.contrib.taxcalcstyle.param import TaxcalcStyleParam


class TaxcalcDisplayer(Displayer):
    param_class = TaxcalcStyleParam

    def package_defaults(self):
        return taxcalc_pckg_defaults(**self.meta_parameters)