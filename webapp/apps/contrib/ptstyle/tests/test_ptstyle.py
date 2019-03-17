import os
import json

import pytest
from django import forms

from paramtools import Parameters, ValidationError

from webapp.apps.comp.meta_parameters import translate_to_django
from webapp.apps.comp.displayer import Displayer
from webapp.apps.comp.fields import ValueField, SeparatedValueField
from webapp.apps.comp.parser import BaseParser
from webapp.apps.users.models import Project

from webapp.apps.contrib.utils import IOClasses
from webapp.apps.contrib.ptstyle.param import ParamToolsParam
from webapp.apps.contrib.ptstyle.parser import ParamToolsParser
from webapp.apps.contrib.ptstyle.utils import dims_to_dict, dims_to_string

CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))


@pytest.fixture
def schema_def_path():
    pwd = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(pwd, "schema.json")


@pytest.fixture
def defaults_spec_path():
    pwd = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(pwd, "defaults.json")


@pytest.fixture
def TestParams(schema_def_path, defaults_spec_path):
    class _TestParams(Parameters):
        schema = schema_def_path
        defaults = defaults_spec_path

    return _TestParams


@pytest.fixture
def pt_metaparam(TestParams):
    return translate_to_django(
        {
            "meta_parameters": {
                "dim0": {
                    "title": "dim 0",
                    "type": "str",
                    "default": "zero",
                    "validators": {"choice": {"choices": ["zero", "one"]}},
                }
            }
        }
    )


def test_make_params(TestParams):
    params = TestParams()
    assert params


def test_param(TestParams, pt_metaparam):
    params = TestParams()
    mp_inst = {mp.name: mp.default for mp in pt_metaparam.parameters}
    spec = params.specification(meta_data=True, **mp_inst)
    for param, attrs in spec.items():
        param = ParamToolsParam(param, attrs, **mp_inst)
        assert param
        assert param.fields
        value = attrs["value"]
        assert len(param.fields) == len(value)


def test_make_field_types(TestParams, pt_metaparam):
    params = TestParams()
    mp_inst = {mp.name: mp.default for mp in pt_metaparam.parameters}
    spec = params.specification(meta_data=True, **mp_inst)

    param = ParamToolsParam("str_choice_param", spec["str_choice_param"])
    assert isinstance(param.fields["str_choice_param"], forms.TypedChoiceField)

    param = ParamToolsParam("min_int_param", spec["min_int_param"])
    assert all([isinstance(field, ValueField) for _, field in param.fields.items()])

    param = ParamToolsParam("int_array_param", spec["int_array_param"])
    assert all(
        [isinstance(field, SeparatedValueField) for _, field in param.fields.items()]
    )


def test_param_naming(TestParams, pt_metaparam):
    raw_meta_params = {"dim0": "zero"}
    mp_inst = pt_metaparam.validate(raw_meta_params)
    params = TestParams()
    spec = params.specification(meta_data=True, **mp_inst)

    pname = "min_int_param"
    fake_vi = {"dim0": "one", "dim1": "heyo", "dim2": "byo", "value": 123}
    param = ParamToolsParam(pname, spec[pname], **mp_inst)
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
    param = ParamToolsParam(pname, spec[pname], **mp_inst)
    newname, suffix = dims_to_string(pname, fake_vi, mp_inst)
    assert suffix == ""
    assert newname == pname


def test_param_parser(db, TestParams, pt_metaparam):
    # set up test data and classes
    raw_meta_params = {"dim0": "zero"}
    valid_meta_params = pt_metaparam.validate(raw_meta_params)
    test_params = TestParams()

    class MockDisplayer(Displayer):
        def package_defaults(self):
            return {
                "test": test_params.specification(meta_data=True, **valid_meta_params)
            }

    class MockParser(ParamToolsParser):
        def parse_parameters(self):
            params, _, errors_warnings = BaseParser.parse_parameters(self)
            test_params = TestParams()
            test_params.adjust(params["test"], raise_errors=False)
            errors_warnings["test"]["errors"] = test_params.errors
            return (params, {"test": json.dumps(params["test"])}, errors_warnings)

    ioclasses = IOClasses(
        Parser=MockParser, Param=ParamToolsParam, Displayer=MockDisplayer
    )
    project = Project.objects.get(title="Used-for-testing")

    # test good data; make sure there are no warnings/errors
    inputs = {
        "min_int_param____dim0__mp___dim1__1": 1,
        "min_int_param____dim0__mp___dim1__2": 2,
        "str_choice_param": "value1",
    }
    parser = MockParser(project, ioclasses, inputs, **valid_meta_params)
    parsed = parser.parse_parameters()
    assert parsed
    params, jsonstrs, errors_warnings = parsed
    exp = {
        "min_int_param": [
            {"value": 1, "dim0": "zero", "dim1": "1"},
            {"value": 2, "dim0": "zero", "dim1": "2"},
        ],
        "str_choice_param": [{"value": "value1"}],
    }
    assert dict(params["test"]) == exp
    assert jsonstrs
    for ew in errors_warnings.values():
        assert ew == {"errors": {}, "warnings": {}}

    inputs = {
        "min_int_param____dim0__mp___dim1__1": -1,
        "min_int_param____dim0__mp___dim1__2": -2,
        "str_choice_param": "notachoice",
    }
    parser = MockParser(project, ioclasses, inputs, **valid_meta_params)
    parsed = parser.parse_parameters()
    assert parsed
    params, jsonstrs, errors_warnings = parsed
    exp = {
        "min_int_param": [
            {"value": -1, "dim0": "zero", "dim1": "1"},
            {"value": -2, "dim0": "zero", "dim1": "2"},
        ],
        "str_choice_param": [{"value": "notachoice"}],
    }
    assert dict(params["test"]) == exp
    assert jsonstrs
    assert len(errors_warnings["test"]["errors"]["min_int_param"]) == 2
    assert len(errors_warnings["test"]["errors"]["str_choice_param"]) == 1
