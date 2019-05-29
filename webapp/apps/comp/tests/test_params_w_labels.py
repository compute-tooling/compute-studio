import os
import json
from typing import Type

import pytest
from django import forms

from paramtools import Parameters, ValidationError

from webapp.apps.comp.meta_parameters import translate_to_django, MetaParameters
from webapp.apps.comp.displayer import Displayer
from webapp.apps.comp.fields import ValueField
from webapp.apps.comp.tests.parser import LocalParser
from webapp.apps.users.models import Project
from webapp.apps.comp.ioutils import get_ioutils
from webapp.apps.comp.param import Param
from webapp.apps.comp.utils import dims_to_dict, dims_to_string

CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))


@pytest.fixture
def defaults_spec_path() -> str:
    pwd = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(pwd, "inputs_w_labels.json")


@pytest.fixture
def TestParams(defaults_spec_path: str) -> Type[Parameters]:
    class _TestParams(Parameters):
        defaults = defaults_spec_path

    return _TestParams


@pytest.fixture
def pt_metaparam_dict() -> dict:
    return {
        "dim0": {
            "title": "dim 0",
            "description": "ex metaparam",
            "type": "str",
            "value": "zero",
            "validators": {"choice": {"choices": ["zero", "one"]}},
        }
    }


@pytest.fixture
def pt_metaparam(pt_metaparam_dict: dict) -> MetaParameters:
    return translate_to_django(pt_metaparam_dict)


def test_make_params(TestParams: Parameters):
    params = TestParams()
    assert params


def test_param(TestParams: Parameters, pt_metaparam: dict):
    params = TestParams()
    mp_inst = pt_metaparam.validate({})
    spec = params.specification(meta_data=True, **mp_inst)
    for param, attrs in spec.items():
        param = Param(param, attrs, **mp_inst)
        assert param
        assert param.fields
        value = attrs["value"]
        assert len(param.fields) == len(value)


def test_make_field_types(TestParams: Parameters, pt_metaparam: dict):
    params = TestParams()
    mp_inst = pt_metaparam.validate({})
    spec = params.specification(meta_data=True, **mp_inst)

    param = Param("str_choice_param", spec["str_choice_param"])
    assert isinstance(param.fields["str_choice_param"], forms.TypedChoiceField)

    param = Param("min_int_param", spec["min_int_param"])
    assert all([isinstance(field, ValueField) for _, field in param.fields.items()])

    param = Param("int_array_param", spec["int_array_param"])
    assert all([isinstance(field, ValueField) for _, field in param.fields.items()])


def test_param_naming(TestParams: Parameters, pt_metaparam: dict):
    raw_meta_params = {"dim0": "zero"}
    mp_inst = pt_metaparam.validate(raw_meta_params)
    params = TestParams()
    spec = params.specification(meta_data=True, **mp_inst)

    pname = "min_int_param"
    fake_vi = {"dim0": "one", "dim1": "heyo", "dim2": "byo", "value": 123}
    param = Param(pname, spec[pname], **mp_inst)
    newname, suffix = dims_to_string(pname, fake_vi, mp_inst)
    assert suffix == "dim0__mp___dim1__heyo___dim2__byo"
    assert newname == pname + "____" + suffix

    param.set_fields([fake_vi])
    exp = "min_int_param____dim0__mp___dim1__heyo___dim2__byo"
    assert param.col_fields[-1].name == exp
    assert param.col_fields[-1].default_value == 123
    assert exp in param.fields

    pname = "min_int_param"
    fake_vi = {"value": 123}
    param = Param(pname, spec[pname], **mp_inst)
    newname, suffix = dims_to_string(pname, fake_vi, mp_inst)
    assert suffix == ""
    assert newname == pname


def test_paramparser(
    db, TestParams: Parameters, pt_metaparam: dict, pt_metaparam_dict: dict
):
    # set up test data and classes
    raw_meta_params = {"dim0": "zero"}
    valid_meta_params = pt_metaparam.validate(raw_meta_params)
    test_params = TestParams()

    class MockDisplayer(Displayer):
        def package_defaults(self):
            return (
                pt_metaparam_dict,
                {
                    "test": test_params.specification(
                        meta_data=True, **valid_meta_params
                    )
                },
            )

    class MockParser(LocalParser):
        def parse_parameters(self):
            errors_warnings, params, _ = super().parse_parameters()
            test_params = TestParams()
            test_params.adjust(params["test"], raise_errors=False)
            errors_warnings["test"]["errors"] = test_params.errors
            return (errors_warnings, params, None)

    project = Project.objects.get(title="Used-for-testing")
    ioutils = get_ioutils(project=project, Parser=MockParser, Displayer=MockDisplayer)

    # test good data; make sure there are no warnings/errors
    inputs = {
        "min_int_param____dim0__mp___dim1__1": 1,
        "min_int_param____dim0__mp___dim1__2": 2,
        "str_choice_param": "value1",
    }
    parser = MockParser(project, ioutils.displayer, inputs, **valid_meta_params)
    errors_warnings, params, _ = parser.parse_parameters()
    assert errors_warnings
    assert params
    exp = {
        "min_int_param": [
            {"value": 1, "dim0": "zero", "dim1": "1"},
            {"value": 2, "dim0": "zero", "dim1": "2"},
        ],
        "str_choice_param": [{"value": "value1"}],
    }
    assert dict(params["test"]) == exp
    for ew in errors_warnings.values():
        assert ew == {"errors": {}, "warnings": {}}

    inputs = {
        "min_int_param____dim0__mp___dim1__1": -1,
        "min_int_param____dim0__mp___dim1__2": -2,
        "str_choice_param": "notachoice",
    }
    parser = MockParser(project, ioutils.displayer, inputs, **valid_meta_params)
    errors_warnings, params, _ = parser.parse_parameters()
    assert errors_warnings
    assert params
    exp = {
        "min_int_param": [
            {"value": -1, "dim0": "zero", "dim1": "1"},
            {"value": -2, "dim0": "zero", "dim1": "2"},
        ],
        "str_choice_param": [{"value": "notachoice"}],
    }
    assert dict(params["test"]) == exp
    assert len(errors_warnings["test"]["errors"]["min_int_param"]) == 2
    assert len(errors_warnings["test"]["errors"]["str_choice_param"]) == 1
