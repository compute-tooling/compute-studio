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
