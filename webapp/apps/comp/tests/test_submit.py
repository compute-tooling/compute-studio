import json

from django.test import RequestFactory

from webapp.apps.contrib.utils import IOClasses
from webapp.apps.users.models import Project

from webapp.apps.comp.submit import Submit, Save
from webapp.apps.comp.displayer import Displayer
from webapp.apps.comp.models import Inputs, Simulation
from webapp.apps.comp.param import Param
from webapp.apps.comp.parser import BaseParser
from webapp.apps.comp.forms import InputsForm
from .compute import MockCompute

from .mockclasses import MockModel


def test_submit(db, comp_inputs, meta_param, profile):
    class MockDisplayer(Displayer):
        def package_defaults(self):
            return comp_inputs

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
    inputs = Inputs.objects.get(pk=submit.model.pk)
    assert inputs.meta_parameters
    assert inputs.raw_gui_inputs
    assert inputs.gui_inputs
    assert inputs.inputs_file
    assert inputs.model_parameters
    assert inputs.inputs_style
    assert inputs.project
    save = Save(submit)
    sim = Simulation.objects.get(pk=save.runmodel_instance.pk)
    assert sim.owner
    assert sim.sponsor is None
    assert sim.project
    assert sim.model_pk == Simulation.objects.next_model_pk(sim.project) - 1


def test_submit_sponsored(db, comp_inputs, meta_param, profile):
    class MockDisplayer(Displayer):
        def package_defaults(self):
            return comp_inputs

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
    inputs = Inputs.objects.get(pk=submit.model.pk)
    assert inputs.meta_parameters
    assert inputs.raw_gui_inputs
    assert inputs.gui_inputs
    assert inputs.inputs_file
    assert inputs.model_parameters
    assert inputs.inputs_style
    assert inputs.project
    save = Save(submit)
    sim = Simulation.objects.get(pk=save.runmodel_instance.pk)
    assert sim.owner
    assert sim.sponsor
    assert sim.project
    assert sim.model_pk == Simulation.objects.next_model_pk(sim.project) - 1


def test_submit_w_errors(db, comp_inputs, meta_param, profile):
    mock_errors_warnings = {
        "test": {"errors": {"testing": ["an error"]}, "warnings": {}}
    }

    class MockDisplayer(Displayer):
        def package_defaults(self):
            return comp_inputs

    class MockParser(BaseParser):
        def parse_parameters(self):
            params, jsonstr, errors_warnings = super().parse_parameters()
            jsonstr = json.dumps({"testing": [1, 2, 3]})
            return params, jsonstr, mock_errors_warnings

    ioclasses = IOClasses(Displayer=MockDisplayer, Parser=MockParser, Param=Param)
    project = Project.objects.get(title="Used-for-testing")

    factory = RequestFactory()
    data = {"has_errors": ["False"], "metaparam": ["3"], "intparam": ["1"]}
    request = factory.post("/modeler/Used-for-testing/sim", data)
    request.user = profile.user
    compute = MockCompute()
    submit = Submit(request, project, ioclasses, compute)
    assert submit.stop_submission
    assert submit.model.errors_warnings == mock_errors_warnings
    assert "<p>testing:</p><ul><li>an error</li></ul>" in submit.form.errors["__all__"]
