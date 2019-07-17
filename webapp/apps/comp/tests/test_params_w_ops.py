import os
import json
from typing import Type

import pytest
from django import forms

from paramtools import Parameters, ValidationError

from webapp.apps.comp.meta_parameters import translate_to_django, MetaParameters
from webapp.apps.comp.displayer import Displayer
from webapp.apps.comp.fields import ValueField
from webapp.apps.comp.forms import InputsForm
from webapp.apps.comp.tests.parser import LocalParser
from webapp.apps.users.models import Project
from webapp.apps.comp.ioutils import get_ioutils
from webapp.apps.comp.param import Param
from webapp.apps.comp.utils import dims_to_dict, dims_to_string

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
    valid_meta_params = ext_metaparam.validate({})
    test_params = ExtParams()

    class MockDisplayer(Displayer):
        def package_defaults(self):
            return (
                ext_metaparam_dict,
                {
                    "policy": test_params.specification(
                        meta_data=True, **valid_meta_params
                    )
                },
            )

    class MockParser(LocalParser):
        def parse_parameters(self):
            errors_warnings, params, _ = super().parse_parameters()
            test_params = ExtParams()
            test_params.adjust(params["policy"], raise_errors=False)
            errors_warnings["policy"]["errors"] = test_params.errors
            return (errors_warnings, params, None)

    project = Project.objects.get(title="Tax-Brain")
    ioutils = get_ioutils(project=project, Parser=MockParser, Displayer=MockDisplayer)

    # test good data; make sure there are no warnings/errors
    raw_inputs = {
        "CPI_offset____year__mp": "<,-0.001,*",
        "STD____MARS__single___year__mp": "4000,*,*,6000",
        "STD____MARS__mjoint___year__mp": "*,5000",
        "STD____MARS__mseparate___year__mp": "1000",
        "II_em____year__mp": "*,*,1000",
    }
    form = InputsForm(project, ioutils.displayer, raw_inputs)
    assert form.is_valid()
    inputs = form.cleaned_data

    parser = MockParser(project, ioutils.displayer, inputs, **valid_meta_params)
    errors_warnings, params, _ = parser.parse_parameters()
    assert errors_warnings
    assert params

    exp = {
        "CPI_offset": [{"year": 2018, "value": -0.001}],
        "STD": [
            {"MARS": "single", "year": 2019, "value": 4000.0},
            {"MARS": "single", "year": 2022, "value": 6000.0},
            {"MARS": "mjoint", "year": 2020, "value": 5000.0},
            {"MARS": "mseparate", "year": 2019, "value": 1000.0},
        ],
        "II_em": [{"year": 2021, "value": 1000.0}],
    }

    assert params["policy"] == exp


def test_param_parser_error(
    db, ExtParams: Parameters, ext_metaparam: dict, ext_metaparam_dict: dict
):
    # set up test data and classes
    valid_meta_params = ext_metaparam.validate({})
    test_params = ExtParams()

    class MockDisplayer(Displayer):
        def package_defaults(self):
            return (
                ext_metaparam_dict,
                {
                    "policy": test_params.specification(
                        meta_data=True, **valid_meta_params
                    )
                },
            )

    class MockParser(LocalParser):
        def parse_parameters(self):
            errors_warnings, params, _ = super().parse_parameters()
            test_params = ExtParams()
            test_params.adjust(params["policy"], raise_errors=False)
            errors_warnings["policy"]["errors"] = test_params.errors
            return (errors_warnings, params, None)

    project = Project.objects.get(title="Tax-Brain")
    ioutils = get_ioutils(project=project, Parser=MockParser, Displayer=MockDisplayer)

    # test good data; make sure there are no warnings/errors
    raw_inputs = {"CPI_offset____year__mp": "<"}
    form = InputsForm(project, ioutils.displayer, raw_inputs)
    assert form.is_valid()
    inputs = form.cleaned_data

    parser = MockParser(project, ioutils.displayer, inputs, **valid_meta_params)
    errors_warnings, params, _ = parser.parse_parameters()
    assert errors_warnings
    assert params

    exp = {}

    assert params["policy"] == exp
    assert errors_warnings["GUI"]["errors"]["CPI_offset"] == [
        "Reverse operator must have an additional value, e.g. '<,2'"
    ]

    raw_inputs = {"CPI_offset____year__mp": "-0.001,<,-0.002"}
    form = InputsForm(project, ioutils.displayer, raw_inputs)
    assert form.is_valid()
    inputs = form.cleaned_data

    parser = MockParser(project, ioutils.displayer, inputs, **valid_meta_params)
    errors_warnings, params, _ = parser.parse_parameters()
    assert params["policy"] == exp
    assert errors_warnings["GUI"]["errors"]["CPI_offset"] == [
        "Reverse operator can only be used in the first position."
    ]

    raw_inputs = {"CPI_offset____year__mp": "*,<,-0.002"}
    form = InputsForm(project, ioutils.displayer, raw_inputs)
    assert form.is_valid()
    inputs = form.cleaned_data

    parser = MockParser(project, ioutils.displayer, inputs, **valid_meta_params)
    errors_warnings, params, _ = parser.parse_parameters()
    assert params["policy"] == exp
    assert errors_warnings["GUI"]["errors"]["CPI_offset"] == [
        "Reverse operator can only be used in the first position."
    ]
