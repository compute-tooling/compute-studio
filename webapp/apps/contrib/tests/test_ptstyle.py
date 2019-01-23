import os
import json

import pytest
from django import forms

from paramtools import parameters

from webapp.apps.core.meta_parameters import meta_parameters, MetaParameter
from webapp.apps.core.displayer import Displayer
from webapp.apps.contrib.ptstyle.param import ParamToolsParam
from webapp.apps.contrib.ptstyle.parser import ParamToolsParser

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
    class _TestParams(parameters.Parameters):
        schema = schema_def_path
        defaults = defaults_spec_path

    return _TestParams


@pytest.fixture
def pt_metaparam(TestParams):
    meta_parameters.parameters.append(
        MetaParameter(
            name="dim0",
            default="zero",
            field=forms.ChoiceField(choices=list((i, i) for i in ["zero", "one"]))
        ),
    )
    return meta_parameters


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


def test_param_naming(TestParams, pt_metaparam):
    raw_meta_params = {"dim0": "zero"}
    mp_inst = meta_parameters.validate(raw_meta_params)
    params = TestParams()
    spec = params.specification(meta_data=True, **mp_inst)

    pname = "min_int_param"
    fake_vi = {"dim0": "one", "dim1": "heyo", "dim2": "byo", "value": 123}
    param = ParamToolsParam(pname, spec[pname], **mp_inst)
    assert param.name_from_dims(fake_vi) == "dim0_one__dim1_heyo__dim2_byo"

    param.set_fields([fake_vi])
    exp = "min_int_param___dim0_one__dim1_heyo__dim2_byo"
    assert param.col_fields[-1].name == exp
    assert param.col_fields[-1].default_value == 123
    assert exp in param.fields


def test_param_parser(TestParams):
    # set up test data and classes
    raw_meta_params = {"dim0": "zero"}
    valid_meta_params = meta_parameters.validate(raw_meta_params)
    test_params = TestParams()

    class MockDisplayer(Displayer):
        param_class = ParamToolsParam

        def package_defaults(self):
            return {"test": test_params.specification(meta_data=True,
                                                      **valid_meta_params)}

    class MockParser(ParamToolsParser):
        displayer_class = MockDisplayer

        def parse_parameters(self):
            params, _, errors_warnings = super().parse_parameters()
            test_params = TestParams()
            test_params.adjust(params["test"], raise_errors=False)
            errors_warnings["test"]["errors"] = test_params.errors
            return (
                params,
                {"test": json.dumps(params["test"])},
                errors_warnings
            )

    # test good data; make sure there are no warnings/errors
    inputs = {
        "min_int_param___dim0_zero__dim1_1": 1,
        "str_choice_param": "value1"
    }
    parser = MockParser(inputs, **valid_meta_params)
    parsed = parser.parse_parameters()
    assert parsed
    params, jsonstrs, errors_warnings = parsed
    assert params["test"]["min_int_param"][0]["value"] == 1
    assert params["test"]["str_choice_param"][0]["value"] == "value1"
    assert jsonstrs
    for ew in errors_warnings.values():
        assert ew == {"errors": {}, "warnings": {}}
