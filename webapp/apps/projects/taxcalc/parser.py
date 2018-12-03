from webapp.apps.contrib.taxcalcstyle.parser import TaxcalcStyleParser
from .displayer import TaxcalcDisplayer


class TaxcalcParser(TaxcalcStyleParser):
    displayer_class = TaxcalcDisplayer