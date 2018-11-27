from webapp.apps.core import submit
from webapp.apps.projects.taxcalc.forms import Form
from webapp.apps.projects.taxcalc.param_parser import ParamParser
from webapp.apps.projects.taxcalc.models import TaxcalcInputs, TaxcalcRun
from webapp.apps.projects.taxcalc.constants import TAXCALC_VERSION, NUM_BUDGET_YEARS


class Submit(submit.Submit):

    Name = "taxcalc"
    ParamParserCls = ParamParser
    FormCls = Form
    InputModelCls = TaxcalcInputs
    upstream_version = TAXCALC_VERSION
    task_run_time_secs = 25

    def __init__(self, request, compute, **kwargs):
        super().__init__(request, compute, **kwargs)

    def get_fields(self):
        super().get_fields()
        print("start_year: ", self.fields.get("start_year"))
        print("data_source: ", self.fields.get("data_source"))
        start_year = self.fields.get("start_year", START_YEAR)
        if hasattr(start_year, 'isdigit') and start_year.isdigit():
            start_year = int(start_year)
        data_source = self.fields.get("data_source", "PUF")
        use_puf_not_cps = data_source == "PUF"
        self.meta_parameters.update({
            "start_year": start_year,
            "data_source": data_source,
            "use_puf_not_cps": use_puf_not_cps,
        })

    def extend_data(self, data):
        num_years = 1 if self.is_quick_calc else NUM_BUDGET_YEARS
        data_list = [dict(year_n=i, **data) for i in range(0, num_years)]
        return data_list


class Save(submit.Save):

    ProjectName = "Tax-Calculator"
    RunModelCls = TaxcalcRun
