import pytest

from webapp.apps.core.param import Param, CheckBox
from webapp.apps.core.displayer import Displayer
from webapp.apps.core.parser import Parser
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
            assert all(getattr(param, name)
                       for name in valid_meta_params.keys())
            param.set_fields([1])
            assert param.col_fields
            assert param.fields


def test_checkboxfield():
    checkbox = CheckBox(
        "test",
        "label",
        True)
    assert checkbox


def test_paramdisplayer(core_inputs, valid_meta_params):
    """
    Test ParamDisplayer class
    """
    class MockDisplayer(Displayer):
        param_class = Param

        def package_defaults(self):
            return core_inputs

    displayer = MockDisplayer(**valid_meta_params)
    assert displayer
    flatdict = displayer.defaults(flat=True)
    nesteddict = displayer.defaults(flat=False)
    assert set(flatdict.keys()) == {"intparam", "boolparam", "floatparam",
                                    "mj2param", "zerodimparam"}
    assert all(isinstance(v , Param) for v in flatdict.values())
    assert list(nesteddict.keys()) == ["majorsection1", "majorsection2"]
    assert (len(nesteddict["majorsection1"]) == 2 and
            len(nesteddict["majorsection2"]) == 1)


def test_paramparser(core_inputs, valid_meta_params):
    """

    """
    class MockDisplayer(Displayer):
        param_class = Param

        def package_defaults(self):
            return core_inputs

    class MockParser(Parser):
        displayer_class = MockDisplayer

        def package_defaults(self):
            return core_inputs

    clean_inputs = {
        "intparam": [3],
        "mj2param": [4.0],
    }
    parser = MockParser(clean_inputs, **valid_meta_params)
    res, _, _ = parser.parse_parameters()
    assert res == {"majorsection1": {"intparam": [3]},
                   "majorsection2": {"mj2param": [4.0]}}


def test_form(core_inputs, meta_param):
    class MockDisplayer(Displayer):
        param_class = Param

        def package_defaults(self):
            return core_inputs

    class MockInputsForm(InputsForm):
        displayer_class = MockDisplayer
        model = MockModel
        meta_parameters = meta_param

    # case with no data
    form = MockInputsForm({})
    assert form

    # case with good data
    raw_inputs = {"intparam": "3,5", "mj2param": "4.0", "boolparam": "True"}
    form = MockInputsForm(raw_inputs)
    assert form.is_valid()
    exp = {"intparam": [3, 5], "mj2param": [4.0], "boolparam": [True]}
    for k, v in exp.items():
        assert form.cleaned_data[k] == v
    model = form.save(MockModel)
    assert model.raw_gui_inputs
    assert model.gui_inputs
    assert model.metaparam

    # case with bad data
    raw_inputs = {"intparam": "abc"}
    form = MockInputsForm(raw_inputs)
    assert not form.is_valid()
    assert "intparam" in form.errors
