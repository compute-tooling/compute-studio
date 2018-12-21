import json

from django.test import RequestFactory

from webapp.apps.core.submit import Submit, Save
from webapp.apps.core.displayer import Displayer
from webapp.apps.core.param import Param
from webapp.apps.core.parser import Parser
from webapp.apps.core.forms import InputsForm
from .compute import MockCompute

from .mockclasses import MockModel


def test_submit(core_inputs, meta_param, profile):

    class MockDisplayer(Displayer):
        param_class = Param

        def package_defaults(self):
            return core_inputs

    class MockParser(Parser):
        displayer_class = MockDisplayer

        def package_defaults(self):
            return core_inputs

        def parse_parameters(self):
            params, jsonstr, errors_warnings = super().parse_parameters()
            jsonstr = json.dumps({"testing": [1, 2, 3]})
            return params, jsonstr, errors_warnings

    class MockInputsForm(InputsForm):
        displayer_class = MockDisplayer
        model = MockModel
        meta_parameters = meta_param

    class MockSubmit(Submit):
        parser_class = MockParser
        form_class = MockInputsForm
        upstream_version = "0.1.0"
        task_run_time_secs = 10
        meta_parameters = meta_param

    class MockSave(Save):
        project_name = "Used strictly for testing"
        runmodel = MockModel


    factory = RequestFactory()
    data = {
        "has_errors": ["False"],
        "metaparam": ["3"],
        "intparam": ["1"]
    }
    request = factory.post("/mockcore", data)
    request.user = profile.user
    compute = MockCompute()
    submit = MockSubmit(request, compute)
    assert not submit.stop_submission
    assert submit.model.upstream_parameters
    assert submit.model.inputs_file
    assert submit.model.errors_warnings
    save = MockSave(submit)
    assert save.runmodel_instance
