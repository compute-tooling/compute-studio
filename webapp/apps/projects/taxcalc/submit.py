from webapp.apps.core import submit
from .forms import TaxcalcInputsForm
from .param_parser import ParamParser
from .models import TaxcalcInputs, TaxcalcRun
from .constants import (TAXCALC_VERSION, NUM_BUDGET_YEARS, START_YEAR,
                        DEFAULT_SOURCE)
from .meta_parameters import meta_parameters


class Submit(submit.Submit):

    Name = "taxcalc"
    ParamParserCls = ParamParser
    FormCls = TaxcalcInputsForm
    InputModelCls = TaxcalcInputs
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


class Save(submit.Save):

    ProjectName = "Tax-Calculator"
    RunModelCls = TaxcalcRun
