import os

from webapp.apps.core.tests.test_views import CoreAbstractViewsTest
from webapp.apps.core.tests.compute import MockCompute
from webapp.apps.projects.{project}.models import {Project}Run

def read_outputs():
    curr = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(curr, 'outputs.json'), 'r') as f:
        outputs = f.read()
    return outputs

class {Project}MockCompute(MockCompute):
    outputs = read_outputs()

class Test{Project}(CoreAbstractViewsTest):
    """
    Inherits test cases and functionality from CoreAbstractViewsTest
    """
    app_name = '{project}'
    mockcompute = {Project}MockCompute
    RunModel = {Project}Run

    def inputs_ok(self):
        inputs = super().inputs_ok()
        upstream_inputs = {}
        return dict(inputs, **upstream_inputs)

    def outputs_ok(self):
        return read_outputs()
