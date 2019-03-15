import json
import os

import pytest

from webapp.apps.core.displayer import Displayer
from webapp.apps.core.meta_parameters import translate_to_django
from webapp.apps.contrib.taxcalcstyle.parser import TaxcalcStyleParser
from webapp.apps.contrib.taxcalcstyle.param import TaxcalcStyleParam


@pytest.fixture
def mockparam():
    path = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(path, "mocktaxcalc_inputs.json")) as f:
        return json.loads(f.read())


@pytest.fixture
def meta_parameters():
    meta_parameters = {
        "meta_parameters": {
            "start_year": {
                "title": "Start Year",
                "type": "int",
                "default": 2017,
                "validators": {"range": {"min": 2013, "max": 2028}},
            },
            "data_source": {
                "title": "Data Source",
                "type": "str",
                "default": "PUF",
                "validators": {"choice": {"choices": ["PUF", "CPS"]}},
            },
            "use_full_sample": {
                "title": "Use full sample",
                "type": "bool",
                "default": True,
                "validators": {},
            },
        }
    }
    return translate_to_django(meta_parameters)


def test_param(mockparam, meta_parameters):
    mp_inst = {mp.name: mp.default for mp in meta_parameters.parameters}
    for name, attrs in mockparam["policy"].items():
        param = TaxcalcStyleParam(name, attrs, **mp_inst)
        assert param
        assert param.fields
        value = attrs["value"]
        if isinstance(value[0], list):
            assert len(param.col_fields) == len(value[0])
        if attrs["cpi_inflatable"]:
            assert param.cpi_field


@pytest.mark.requires_taxcalc
def test_param_parser(mockparam):

    # set up test data and classes
    raw_meta_params = {
        "start_year": "2018",
        "data_source": "PUF",
        "use_full_sample": "False",
    }
    valid_meta_params = meta_parameters.validate(raw_meta_params)

    class MockDisplayer(Displayer):
        param_class = TaxcalcStyleParam

        def package_defaults(self):
            return mockparam

    class MockParser(TaxcalcStyleParser):
        displayer_class = MockDisplayer

    # test good data; make sure there are no warnings/errors
    parser = MockParser({"_STD_0": [10001], "_BE_sub": [0.2]}, **valid_meta_params)
    parsed = parser.parse_parameters()
    assert parsed
    params, jsonstrs, errors_warnings = parsed
    assert params["policy"][2018]["_STD"][0][0] == 10001
    assert params["behavior"][2018]["_BE_sub"][0] == 0.2
    assert jsonstrs
    for ew in errors_warnings.values():
        assert ew == {"errors": {}, "warnings": {}}

    # test bad data; make sure there are warnings/errors
    parser = MockParser({"_STD_0": [-2], "_BE_sub": [-1]}, **valid_meta_params)
    parsed = parser.parse_parameters()
    assert parsed
    params, jsonstrs, errors_warnings = parsed
    assert params["policy"][2018]["_STD"][0][0] == -2
    assert params["behavior"][2018]["_BE_sub"][0] == -1
    assert jsonstrs
    for sect in ["policy", "behavior"]:
        assert errors_warnings[sect] != {"errors": {}, "warnings": {}}

    # pin down parse_errors_warnings functionality; needs to be updated if
    # upstream error messages change format
    mockew = {"warnings": "", "errors": "ERROR: 2018 _STD_0 value -2.0 < min value 0\n"}
    exp = {
        "errors": {
            "_STD_0": {"2018": "ERROR: _STD_0 value -2.0 < min value 0 for 2018"}
        },
        "warnings": {},
    }
    assert parser.parse_errors_warnings(mockew) == exp

    # test param look-up functionality
    assert (
        parser.get_default_param("_STD_0", parser.flat_defaults).name == "_STD_single"
    )
    assert parser.get_default_param("_BE_sub", parser.flat_defaults).name == "_BE_sub"
