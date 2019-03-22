import json
import os

import pytest

from webapp.apps.comp.displayer import Displayer
from webapp.apps.comp.parser import BaseParser
from webapp.apps.comp.meta_parameters import translate_to_django
from webapp.apps.users.models import Project

from webapp.apps.contrib.taxcalcstyle.parser import TaxcalcStyleParser
from webapp.apps.contrib.taxcalcstyle.param import TaxcalcStyleParam
from webapp.apps.contrib.utils import IOClasses


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
            assert param.col_fields[0].form_field.clean("<,*")
        if attrs["cpi_inflatable"]:
            assert param.cpi_field


def test_param_parser(db, mockparam, meta_parameters):
    """
    Exercise parser methods using mock data saved from real Tax-Calculator
    usage.
    """

    class MockDisplayer(Displayer):
        def package_defaults(self):
            return mockparam

    class MockParser(TaxcalcStyleParser):
        def parse_parameters(self):
            return BaseParser.parse_parameters(self)

    raw_meta_params = {
        "start_year": "2018",
        "data_source": "PUF",
        "use_full_sample": "False",
    }
    valid_meta_params = meta_parameters.validate(raw_meta_params)
    ioclasses = IOClasses(
        Parser=MockParser, Param=TaxcalcStyleParam, Displayer=MockDisplayer
    )
    project = Project.objects.get(title="Used-for-testing")
    project.input_style = "taxcalc"
    project.save()
    parser = MockParser(
        project,
        ioclasses,
        {"_STD_0": ["<", 10001, "*", 10002], "_BE_sub": [0.2]},
        **valid_meta_params
    )

    params, jsonstr, errors_warnings = parser.parse_parameters()
    assert params == {
        "policy": {"_STD_single": {"2017": [10001], "2019": [10002]}},
        "behavior": {"_BE_sub": {"2018": [0.2]}},
    }
    mock_errors_warnings = {
        "errors": {
            "_STD_0": {
                "2019": "ERROR: _STD_0 value -1.0 < min value 0 for 2019",
                "2020": "ERROR: _STD_0 value -1.0 < min value 0 for 2020",
            }
        },
        "warnings": {},
    }
    exp = {
        "_STD_0": [
            "ERROR: _STD_0 value -1.0 < min value 0 for 2019",
            "ERROR: _STD_0 value -1.0 < min value 0 for 2020",
        ]
    }
    container = {}

    def f(param, msg):
        container[param] = msg

    parser.append_errors_warnings(mock_errors_warnings, f)
    assert container == exp

    # test param look-up functionality
    assert (
        parser.get_default_param("_STD_0", parser.flat_defaults).name == "_STD_single"
    )
    assert parser.get_default_param("_BE_sub", parser.flat_defaults).name == "_BE_sub"
