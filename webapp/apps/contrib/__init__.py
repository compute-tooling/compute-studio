from .ptstyle import register as paramtools_register
from .taxcalcstyle import register as taxcalc_register

register = {"paramtools": paramtools_register, "taxcalc": taxcalc_register}
