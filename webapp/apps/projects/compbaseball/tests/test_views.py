import os

from webapp.apps.core.tests.test_views import CoreAbstractViewsTest
from webapp.apps.core.tests.compute import MockCompute
from webapp.apps.projects.taxcalc.models import CompbaseballRun

def read_outputs():
    curr = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(curr, 'outputs.json'), 'r') as f:
        outputs = f.read()
    return outputs

class CompbaseballMockCompute(MockCompute):
    outputs = read_outputs()

class TestCompbaseball(CoreAbstractViewsTest):
    """
    Inherits test cases and functionality from CoreAbstractViewsTest
    """
    app_name = 'compbaseball'
    mockcompute = CompbaseballMockCompute
    RunModel = CompbaseballRun

    def inputs_ok(self):
        inputs = super().inputs_ok()
        upstream_inputs = {}
        return dict(inputs, **inputs)

    def outputs_ok(self):
        return read_outputs()
