import os
import json
from typing import Type

import pytest
from django import forms

from paramtools import Parameters, ValidationError


from webapp.apps.comp.meta_parameters import translate_to_django, MetaParameters
from webapp.apps.comp.displayer import Displayer
from webapp.apps.comp.fields import ValueField, SeparatedValueField
from webapp.apps.comp.parser import BaseParser
from webapp.apps.users.models import Project

from webapp.apps.comp.ioutils import get_ioutils
from webapp.apps.contrib.ptstyle.param import ParamToolsParam
from webapp.apps.contrib.ptstyle.parser import ParamToolsParser
from webapp.apps.contrib.ptstyle.utils import dims_to_dict, dims_to_string

CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))


@pytest.fixture
def defaults_spec_path() -> str:
    pwd = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(pwd, "taxbrain.json")


@pytest.fixture
def ExtParams(defaults_spec_path: str) -> Type[Parameters]:
    class _ExtParams(Parameters):
        defaults = defaults_spec_path

    return _ExtParams


@pytest.fixture
def ext_metaparam_dict() -> dict:
    return {
        "year": {
            "title": "Start Year",
            "description": "Year for parameters.",
            "type": "int",
            "value": 2019,
            "validators": {"range": {"min": 2019, "max": 2027}},
        },
        "data_source": {
            "title": "Data Source",
            "description": "Data source can be PUF or CPS",
            "type": "str",
            "value": "PUF",
            "validators": {"choice": {"choices": ["PUF", "CPS"]}},
        },
        "use_full_sample": {
            "title": "Use Full Sample",
            "description": "Use entire data set or a 2% sample.",
            "type": "bool",
            "value": False,
            "validators": {"choice": {"choices": [True, False]}},
        },
    }


@pytest.fixture
def ext_metaparam(ext_metaparam_dict: dict) -> MetaParameters:
    return translate_to_django(ext_metaparam_dict)


def test_make_params(ExtParams: Parameters):
    params = ExtParams()
    assert params


def test_param_parser(
    db, ExtParams: Parameters, ext_metaparam: dict, ext_metaparam_dict: dict
):
    # set up test data and classes
    raw_meta_params = {"dim0": "zero"}
    valid_meta_params = ext_metaparam.validate(raw_meta_params)
    test_params = ExtParams()

    class MockDisplayer(Displayer):
        def package_defaults(self):
            return (
                ext_metaparam_dict,
                {
                    "test": test_params.specification(
                        meta_data=True, **valid_meta_params
                    )
                },
            )

    class MockParser(ParamToolsParser):
        def parse_parameters(self):
            params, errors_warnings = BaseParser.parse_parameters(self)
            test_params = ExtParams()
            test_params.adjust(params["test"], raise_errors=False)
            errors_warnings["test"]["errors"] = test_params.errors
            return (params, errors_warnings)

    project = Project.objects.get(title="Tax-Brain")
    ioutils = get_ioutils(project=project, Parser=MockParser, Displayer=MockDisplayer)

    # test good data; make sure there are no warnings/errors
    inputs = {
        "CPI_offset____year__mp": "<,4000,*",
        "STD____MARS__single___year__mp": "4000,*,*,6000",
        "STD____MARS__mjoint___year__mp": "*,5000",
        "II_em": "*,*,1000",
    }
    parser = MockParser(project, ioutils.displayer, inputs, **valid_meta_params)
    parsed = parser.parse_parameters()
    assert parsed
    params, errors_warnings = parsed

    exp = {
        "CPI_offset": [{"year": 2018, "value": 4000}],
        "STD": [
            {"MARS": "single", "year": 2019, "value": 4000},
            {"MARS": "single", "year": 2022, "value": 6000},
            {"MARS": "mjoint", "year": 2020, "value": 5000},
        ],
        "II_em": [{"year": 2021, "value": 1000}],
    }

    assert params == exp
