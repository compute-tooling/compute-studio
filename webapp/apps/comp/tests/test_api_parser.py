from webapp.apps.users.models import Project
from webapp.apps.comp.displayer import Displayer
from webapp.apps.comp.ioutils import get_ioutils
from webapp.apps.comp.tests.parser import LocalAPIParser


def test_api_parser(db, get_inputs, valid_meta_params):
    class MockDisplayer(Displayer):
        def package_defaults(self):
            return get_inputs

    project = Project.objects.get(title="Used-for-testing")
    ioutils = get_ioutils(project, Displayer=MockDisplayer, Parser=LocalAPIParser)
    ioutils.displayer.meta_parameters = valid_meta_params

    clean_inputs = {
        "majorsection1": {"intparam": 3, "boolparam": True},
        "majorsection2": {"mj2param": 4},
    }
    parser = LocalAPIParser(
        project, ioutils.displayer, clean_inputs, **valid_meta_params
    )
    ew, res, _ = parser.parse_parameters()
    assert res == {
        "majorsection1": {"intparam": 3, "boolparam": True},
        "majorsection2": {"mj2param": 4},
    }
    errors_warnings = {"errors": {}, "warnings": {}}
    assert ew["majorsection1"] == errors_warnings
    assert ew["majorsection2"] == errors_warnings
    assert ew["API"] == errors_warnings
    assert ew["GUI"] == errors_warnings


def test_api_parser_extra_section(db, get_inputs, valid_meta_params):
    class MockDisplayer(Displayer):
        def package_defaults(self):
            return get_inputs

    project = Project.objects.get(title="Used-for-testing")
    ioutils = get_ioutils(project, Displayer=MockDisplayer, Parser=LocalAPIParser)
    ioutils.displayer.meta_parameters = valid_meta_params

    clean_inputs = {
        "majorsection1-mispelled": {"intparam": 3, "boolparam": True},
        "majorsection2": {"mj2param": 4},
    }
    parser = LocalAPIParser(
        project, ioutils.displayer, clean_inputs, **valid_meta_params
    )
    ew, res, _ = parser.parse_parameters()
    assert res == {"majorsection1": {}, "majorsection2": {"mj2param": 4}}
    errors_warnings = {"errors": {}, "warnings": {}}
    assert ew["majorsection1"] == errors_warnings
    assert ew["majorsection2"] == errors_warnings
    assert ew["API"] == {
        "errors": {"extra_keys": ["Has extra sections: majorsection1-mispelled"]},
        "warnings": {},
    }
    assert ew["GUI"] == errors_warnings


# TODO: need OPs tests from test_params_w_ops

# good data
# raw_inputs = {
#     "CPI_offset____year__mp": "<,-0.001,*",
#     "STD____MARS__single___year__mp": "4000,*,*,6000",
#     "STD____MARS__mjoint___year__mp": "*,5000",
#     "STD____MARS__mseparate___year__mp": "1000",
#     "II_em____year__mp": "*,*,1000",
# }

# # -->

# exp = {
#     "CPI_offset": [{"year": 2018, "value": -0.001}],
#     "STD": [
#         {"MARS": "single", "year": 2019, "value": 4000.0},
#         {"MARS": "single", "year": 2022, "value": 6000.0},
#         {"MARS": "mjoint", "year": 2020, "value": 5000.0},
#         {"MARS": "mseparate", "year": 2019, "value": 1000.0},
#     ],
#     "II_em": [{"year": 2021, "value": 1000.0}],
# }
###########################

# errors:

# 1.
# raw_inputs = {"CPI_offset____year__mp": "<"}

# exp = {}

# assert params["policy"] == exp
# assert errors_warnings["GUI"]["errors"]["CPI_offset"] == [
#     "Reverse operator must have an additional value, e.g. '<,2'"
# ]
#################

# 2.

# raw_inputs = {"CPI_offset____year__mp": "-0.001,<,-0.002"}

# assert params["policy"] == exp
# assert errors_warnings["GUI"]["errors"]["CPI_offset"] == [
#     "Reverse operator can only be used in the first position."
# ]
###################

# 3.
# raw_inputs = {"CPI_offset____year__mp": "*,<,-0.002"}

# assert params["policy"] == exp
# assert errors_warnings["GUI"]["errors"]["CPI_offset"] == [
#     "Reverse operator can only be used in the first position."
# ]
