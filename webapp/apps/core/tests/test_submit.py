import json

from django.test import RequestFactory

from webapp.apps.contrib.utils import IOClasses
from webapp.apps.users.models import Project

from webapp.apps.core.submit import Submit, Save
from webapp.apps.core.displayer import Displayer
from webapp.apps.core.models import CoreInputs, CoreRun
from webapp.apps.core.param import Param
from webapp.apps.core.parser import BaseParser
from webapp.apps.core.forms import InputsForm
from .compute import MockCompute

from .mockclasses import MockModel


def test_submit(db, core_inputs, meta_param, profile):
    class MockDisplayer(Displayer):
        def package_defaults(self):
            return core_inputs

    class MockParser(BaseParser):
        def parse_parameters(self):
            params, jsonstr, errors_warnings = super().parse_parameters()
            jsonstr = json.dumps({"testing": [1, 2, 3]})
            return params, jsonstr, errors_warnings

    ioclasses = IOClasses(Displayer=MockDisplayer, Parser=MockParser, Param=Param)
    project = Project.objects.get(title="Used-for-testing")

    factory = RequestFactory()
    data = {"has_errors": ["False"], "metaparam": ["3"], "intparam": ["1"]}
    request = factory.post("/modeler/Used-for-testing/sim", data)
    request.user = profile.user
    compute = MockCompute()
    submit = Submit(request, project, ioclasses, compute)
    assert not submit.stop_submission
    inputs = CoreInputs.objects.get(pk=submit.model.pk)
    assert inputs.meta_parameters
    assert inputs.raw_gui_inputs
    assert inputs.gui_inputs
    assert inputs.inputs_file
    assert inputs.upstream_parameters
    assert inputs.input_type
    assert inputs.project
    save = Save(submit)
    sim = CoreRun.objects.get(pk=save.runmodel_instance.pk)
    assert sim.owner
    assert sim.sponsor is None
    assert sim.project


def test_submit_sponsored(db, core_inputs, meta_param, profile):
    class MockDisplayer(Displayer):
        def package_defaults(self):
            return core_inputs

    class MockParser(BaseParser):
        def parse_parameters(self):
            params, jsonstr, errors_warnings = super().parse_parameters()
            jsonstr = json.dumps({"testing": [1, 2, 3]})
            return params, jsonstr, errors_warnings

    ioclasses = IOClasses(Displayer=MockDisplayer, Parser=MockParser, Param=Param)
    project = Project.objects.get(title="Used-for-testing-sponsored-apps")

    factory = RequestFactory()
    data = {"has_errors": ["False"], "metaparam": ["3"], "intparam": ["1"]}
    request = factory.post("/modeler/testapp/sim", data)
    request.user = profile.user
    compute = MockCompute()
    submit = Submit(request, project, ioclasses, compute)
    assert not submit.stop_submission
    inputs = CoreInputs.objects.get(pk=submit.model.pk)
    assert inputs.meta_parameters
    assert inputs.raw_gui_inputs
    assert inputs.gui_inputs
    assert inputs.inputs_file
    assert inputs.upstream_parameters
    assert inputs.input_type
    assert inputs.project
    save = Save(submit)
    sim = CoreRun.objects.get(pk=save.runmodel_instance.pk)
    assert sim.owner
    assert sim.sponsor
    assert sim.project
