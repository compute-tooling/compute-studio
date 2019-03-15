import pytest


from webapp.apps.contrib.utils import IOClasses
from webapp.apps.users.models import Project

from webapp.apps.core.param import Param, CheckBox
from webapp.apps.core.displayer import Displayer
from webapp.apps.core.parser import BaseParser, Parser
from webapp.apps.core.forms import InputsForm

from .mockclasses import MockModel


def test_param(core_inputs, valid_meta_params):
    """
    Test load valid data with core Param class.
    """
    for maj_sect in core_inputs.values():
        for name, attrs in maj_sect.items():
            param = Param(name, attrs, **valid_meta_params)
            assert param
            assert all(getattr(param, name) for name in valid_meta_params.keys())
            param.set_fields([1])
            assert param.col_fields
            assert param.fields


def test_checkboxfield():
    checkbox = CheckBox("test", "label", True)
    assert checkbox


@pytest.fixture
def mockproject(meta_param):
    class MockProject:
        pass

    return MockProject()


def test_paramdisplayer(core_inputs, mockproject, valid_meta_params):
    """
    Test ParamDisplayer class
    """

    class MockDisplayer(Displayer):
        def package_defaults(self):
            return core_inputs

    ioclasses = IOClasses(Displayer=MockDisplayer, Parser=None, Param=Param)
    displayer = MockDisplayer(mockproject, ioclasses, **valid_meta_params)
    assert displayer
    flatdict = displayer.defaults(flat=True)
    nesteddict = displayer.defaults(flat=False)
    assert set(flatdict.keys()) == {
        "intparam",
        "boolparam",
        "floatparam",
        "mj2param",
        "zerodimparam",
    }
    assert all(isinstance(v, Param) for v in flatdict.values())
    assert list(nesteddict.keys()) == ["majorsection1", "majorsection2"]
    assert (
        len(nesteddict["majorsection1"]) == 2 and len(nesteddict["majorsection2"]) == 1
    )


def test_paramparser(core_inputs, valid_meta_params, mockproject):
    """

    """

    class MockDisplayer(Displayer):
        param_class = Param

        def package_defaults(self):
            return core_inputs

    class MockParser(BaseParser):
        pass

    ioclasses = IOClasses(Displayer=MockDisplayer, Parser=Parser, Param=Param)

    clean_inputs = {"intparam": [3], "mj2param": [4.0]}
    parser = MockParser(mockproject, ioclasses, clean_inputs, **valid_meta_params)
    res, _, _ = parser.parse_parameters()
    assert res == {
        "majorsection1": {"intparam": [3]},
        "majorsection2": {"mj2param": [4.0]},
    }


def test_form(db, core_inputs):
    class MockDisplayer(Displayer):
        def package_defaults(self):
            return core_inputs

    ioclasses = IOClasses(Displayer=MockDisplayer, Parser=None, Param=Param)
    project = Project.objects.get(title="Used-for-testing")
    # case with no data
    form = InputsForm(project, ioclasses, {})
    assert form

    # case with good data
    raw_inputs = {"intparam": "3,5", "mj2param": "4.0", "boolparam": "True"}
    form = InputsForm(project, ioclasses, raw_inputs)
    assert form.is_valid()
    exp = {"intparam": [3, 5], "mj2param": [4.0], "boolparam": [True]}
    for k, v in exp.items():
        assert form.cleaned_data[k] == v
    model = form.save()
    assert model.raw_gui_inputs
    assert model.gui_inputs
    assert model.meta_parameters["use_full_data"] is not None

    # case with bad data
    raw_inputs = {"intparam": "abc"}
    form = InputsForm(project, ioclasses, raw_inputs)
    assert not form.is_valid()
    assert "intparam" in form.errors
