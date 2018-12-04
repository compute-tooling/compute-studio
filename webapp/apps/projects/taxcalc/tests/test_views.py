import os

from webapp.apps.core.tests.test_views import CoreAbstractViewsTest
from webapp.apps.core.tests.compute import MockCompute
from webapp.apps.projects.taxcalc.models import TaxcalcRun

def read_outputs():
    curr = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(curr, 'outputs.json'), 'r') as f:
        outputs = f.read()
    return outputs

class UploadMockCompute(MockCompute):
    outputs = read_outputs()

class TestUpload(CoreAbstractViewsTest):
    """
    Inherits test cases and functionality from CoreAbstractViewsTest
    """
    app_name = 'taxcalc'
    mockcompute = UploadMockCompute
    RunModel = TaxcalcRun

    def inputs_ok(self):
        inputs = super().inputs_ok()
        upstream_inputs = {
            "start_year": "2017",
            "data_source": "CPS",
            "use_full_sample": "True",
            "_STD_0": "10000",
            "_STD_cpi": "True",
        }
        return dict(inputs, **inputs)

    def outputs_ok(self):
        return read_outputs()
