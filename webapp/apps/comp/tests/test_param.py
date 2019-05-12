import pytest


from webapp.apps.users.models import Project

from webapp.apps.comp.param import Param, CheckBox
from webapp.apps.comp.displayer import Displayer
from webapp.apps.comp.ioutils import get_ioutils
from webapp.apps.comp.parser import BaseParser, Parser
from webapp.apps.comp.forms import InputsForm

from .mockclasses import MockModel


def test_param(get_inputs, valid_meta_params):
    """
    Test load valid data with comp Param class.
    """
    model_params = get_inputs[1]
    for maj_sect in model_params.values():
        for name, attrs in maj_sect.items():
            param = Param(name, attrs, **valid_meta_params)
            assert param
            assert all(getattr(param, name) for name in valid_meta_params.keys())
            param.set_fields([{"value": 1}])
            assert param.col_fields
            assert param.fields


def test_checkboxfield():
    checkbox = CheckBox("test", "label", True)
    assert checkbox


@pytest.fixture
def mockproject(meta_param):
    class MockProject:
        title = "mock"

    return MockProject()


def test_paramdisplayer(get_inputs, mockproject, valid_meta_params):
    """
    Test ParamDisplayer class
    """

    class MockDisplayer(Displayer):
        def package_defaults(self):
            return get_inputs

    ioutils = get_ioutils(mockproject, Displayer=MockDisplayer, Param=Param)
    ioutils.displayer.meta_parameters = valid_meta_params
    displayer = ioutils.displayer
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


def test_paramparser(get_inputs, valid_meta_params, mockproject, meta_param_dict):
    """

    """

    class MockDisplayer(Displayer):
        def package_defaults(self):
            return get_inputs

    ioutils = get_ioutils(
        mockproject, Displayer=MockDisplayer, Parser=BaseParser, Param=Param
    )
    ioutils.displayer.meta_parameters = valid_meta_params

    clean_inputs = {"intparam": 3, "mj2param": 4.0}
    parser = BaseParser(
        mockproject, ioutils.displayer, clean_inputs, **valid_meta_params
    )
    ew, res = parser.parse_parameters()
    assert res == {
        "majorsection1": {"intparam": [{"value": 3}]},
        "majorsection2": {"mj2param": [{"value": 4.0}]},
    }
    errors_warnings = {"errors": {}, "warnings": {}}
    assert ew["majorsection1"] == errors_warnings
    assert ew["majorsection2"] == errors_warnings


def test_form(db, get_inputs, meta_param_dict):
    class MockDisplayer(Displayer):
        def package_defaults(self):
            return get_inputs

    project = Project.objects.get(title="Used-for-testing")
    ioutils = get_ioutils(project, Displayer=MockDisplayer, Param=Param)
    # case with no data
    form = InputsForm(project, ioutils.displayer, {})
    assert form

    # case with good data
    raw_inputs = {"intparam": "3", "mj2param": "4.0", "boolparam": "True"}
    form = InputsForm(project, ioutils.displayer, raw_inputs)
    assert form.is_valid()
    exp = {"intparam": 3, "mj2param": 4.0, "boolparam": True}
    for k, v in exp.items():
        assert form.cleaned_data[k] == v
    model = form.save()
    assert model.raw_gui_inputs
    assert model.gui_inputs
    assert model.meta_parameters[list(meta_param_dict.keys())[0]] is not None

    # case with bad data
    raw_inputs = {"intparam": "abc"}
    form = InputsForm(project, ioutils.displayer, raw_inputs)
    assert not form.is_valid()
    assert "intparam" in form.errors
