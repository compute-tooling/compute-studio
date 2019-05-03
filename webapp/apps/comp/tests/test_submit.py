import json

from django.test import RequestFactory

from webapp.apps.users.models import Project

from webapp.apps.comp.submit import Submit, Save
from webapp.apps.comp.displayer import Displayer
from webapp.apps.comp.ioutils import get_ioutils
from webapp.apps.comp.models import Inputs, Simulation
from webapp.apps.comp.param import Param
from webapp.apps.comp.parser import BaseParser
from .compute import MockCompute

from .mockclasses import MockModel


def test_submit(db, comp_inputs, meta_param_dict, profile):
    class MockDisplayer(Displayer):
        def package_defaults(self):
            return meta_param_dict, comp_inputs

    class MockParser(BaseParser):
        def parse_parameters(self):
            params, errors_warnings = super().parse_parameters()
            return params, errors_warnings

    project = Project.objects.get(title="Used-for-testing")
    ioutils = get_ioutils(
        project, Displayer=MockDisplayer, Parser=MockParser, Param=Param
    )

    factory = RequestFactory()
    data = {"has_errors": ["False"], "metaparam": ["3"], "intparam": ["1"]}
    request = factory.post("/modeler/Used-for-testing/sim", data)
    request.user = profile.user
    compute = MockCompute()
    submit = Submit(request, project, ioutils, compute)
    assert not submit.stop_submission
    inputs = Inputs.objects.get(pk=submit.model.pk)
    assert inputs.meta_parameters
    assert inputs.raw_gui_inputs
    assert inputs.gui_inputs
    assert inputs.model_parameters
    assert inputs.project
    save = Save(submit)
    sim = Simulation.objects.get(pk=save.runmodel_instance.pk)
    assert sim.owner
    assert sim.sponsor is None
    assert sim.project
    assert sim.model_pk == Simulation.objects.next_model_pk(sim.project) - 1


def test_submit_sponsored(db, comp_inputs, meta_param_dict, profile):
    class MockDisplayer(Displayer):
        def package_defaults(self):
            return meta_param_dict, comp_inputs

    class MockParser(BaseParser):
        def parse_parameters(self):
            params, errors_warnings = super().parse_parameters()
            return params, errors_warnings

    project = Project.objects.get(title="Used-for-testing-sponsored-apps")
    ioutils = get_ioutils(
        project, Displayer=MockDisplayer, Parser=MockParser, Param=Param
    )

    factory = RequestFactory()
    data = {"has_errors": ["False"], "metaparam": ["3"], "intparam": ["1"]}
    request = factory.post("/modeler/testapp/sim", data)
    request.user = profile.user
    compute = MockCompute()
    submit = Submit(request, project, ioutils, compute)
    assert not submit.stop_submission
    inputs = Inputs.objects.get(pk=submit.model.pk)
    assert inputs.meta_parameters
    assert inputs.raw_gui_inputs
    assert inputs.gui_inputs
    assert inputs.model_parameters
    assert inputs.project
    save = Save(submit)
    sim = Simulation.objects.get(pk=save.runmodel_instance.pk)
    assert sim.owner
    assert sim.sponsor
    assert sim.project
    assert sim.model_pk == Simulation.objects.next_model_pk(sim.project) - 1


def test_submit_w_errors(db, comp_inputs, meta_param_dict, profile):
    mock_errors_warnings = {
        "test": {"errors": {"testing": ["an error"]}, "warnings": {}}
    }

    class MockDisplayer(Displayer):
        def package_defaults(self):
            return meta_param_dict, comp_inputs

    class MockParser(BaseParser):
        def parse_parameters(self):
            params, _ = super().parse_parameters()
            return params, mock_errors_warnings

    project = Project.objects.get(title="Used-for-testing")
    ioutils = get_ioutils(
        project, Displayer=MockDisplayer, Parser=MockParser, Param=Param
    )

    factory = RequestFactory()
    data = {"has_errors": ["False"], "metaparam": ["3"], "intparam": ["1"]}
    request = factory.post("/modeler/Used-for-testing/sim", data)
    request.user = profile.user
    compute = MockCompute()
    submit = Submit(request, project, ioutils, compute)
    assert submit.stop_submission
    assert submit.model.errors_warnings == mock_errors_warnings
    assert "<p>testing:</p><ul><li>an error</li></ul>" in submit.form.errors["__all__"]
