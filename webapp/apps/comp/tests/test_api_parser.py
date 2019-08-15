from webapp.apps.users.models import Project
from webapp.apps.comp.displayer import Displayer
from webapp.apps.comp.ioutils import get_ioutils
from webapp.apps.comp.models import Inputs
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
    res = parser.parse_parameters()
    adjustment = res["adjustment"]
    errors_warnings = res["errors_warnings"]
    assert adjustment == {
        "majorsection1": {"intparam": 3, "boolparam": True},
        "majorsection2": {"mj2param": 4},
    }
    exp_errors_warnings = {"errors": {}, "warnings": {}}
    assert errors_warnings["majorsection1"] == exp_errors_warnings
    assert errors_warnings["majorsection2"] == exp_errors_warnings
    assert errors_warnings["API"] == exp_errors_warnings
    assert errors_warnings["GUI"] == exp_errors_warnings


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
    res = parser.parse_parameters()
    adjustment = res["adjustment"]
    errors_warnings = res["errors_warnings"]

    assert adjustment == {"majorsection1": {}, "majorsection2": {"mj2param": 4}}
    exp_errors_warnings = {"errors": {}, "warnings": {}}
    assert errors_warnings["majorsection1"] == exp_errors_warnings
    assert errors_warnings["majorsection2"] == exp_errors_warnings
    assert errors_warnings["API"] == {
        "errors": {"extra_keys": ["Has extra sections: majorsection1-mispelled"]},
        "warnings": {},
    }
    assert errors_warnings["GUI"] == exp_errors_warnings
