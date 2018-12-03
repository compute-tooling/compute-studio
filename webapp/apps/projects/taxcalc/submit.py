from webapp.apps.core.submit import Submit, Save
from .forms import TaxcalcInputsForm
from .parser import TaxcalcParser
from .models import TaxcalcRun
from .constants import TAXCALC_VERSION, NUM_BUDGET_YEARS
from .meta_parameters import meta_parameters


class TaxcalcSubmit(Submit):

    parser_class = TaxcalcParser
    form_class = TaxcalcInputsForm
    upstream_version = TAXCALC_VERSION
    task_run_time_secs = 25
    meta_parameters = meta_parameters

    def extend_data(self, data):
        if not self.valid_meta_params["use_full_sample"]:
            num_years = 1
        else:
            num_years = NUM_BUDGET_YEARS
        data_list = [dict(year_n=i, **data) for i in range(0, num_years)]
        return data_list


class TaxcalcSave(Save):

    project_name = "Tax-Calculator"
    runmodel = TaxcalcRun
