import copy

import pytest
import requests_mock
import paramtools as pt

from webapp.apps.users.models import Project, Profile

from webapp.apps.comp.model_parameters import ModelParameters
from webapp.apps.comp.models import ModelConfig


class MetaParams(pt.Parameters):
    d0: int
    d1: str
    defaults = {
        "d0": {"title": "d0", "description": "", "type": "int", "value": 1},
        "d1": {"title": "d1", "description": "", "type": "str", "value": "hello"},
    }


class Params(pt.Parameters):
    defaults = {
        "schema": {
            "labels": {
                "d0": {"type": "int", "validators": {"range": {"min": 0, "max": 3}}},
                "d1": {
                    "type": "str",
                    "validators": {"choice": {"choices": ["hello", "world"]}},
                },
            }
        },
        "param": {
            "title": "param",
            "description": "test",
            "type": "int",
            "value": [
                {"d0": 1, "d1": "hello", "value": 1},
                {"d0": 1, "d1": "world", "value": 1},
                {"d0": 2, "d1": "hello", "value": 1},
                {"d0": 3, "d1": "world", "value": 1},
            ],
        },
    }


def get_inputs_callback(request, context):
    metaparams = MetaParams(array_first=True)
    metaparams.adjust(request.json()["task_kwargs"]["meta_param_dict"])
    params = Params()
    params.set_state(d0=metaparams.d0.tolist(), d1=metaparams.d1)
    return {
        "status": "SUCCESS",
        "meta_parameters": metaparams.dump(),
        "model_parameters": {"section": params.dump()},
    }


def mock_callback(request, context):
    data = request.json()
    if data["task_name"] == "version":
        return {"status": "SUCCESS", "version": "v1"}
    elif data["task_name"] == "defaults":
        return get_inputs_callback(request, context)
    else:
        raise KeyError(f"Unknown task_name: {task_name}")


@pytest.fixture
def mock_project(db, worker_url):
    profile = Profile.objects.get(user__username="modeler")
    project = Project.objects.create(
        owner=profile,
        title="test",
        status="live",
        description="",
        oneliner="oneliner",
        repo_url="https://repo.com/test",
        exp_task_time=10,
        listed=True,
        sponsor=profile,
    )
    with requests_mock.Mocker() as mock:
        mock.register_uri(
            "POST",
            f"{worker_url}{project.owner}/{project.title}/",
            json=mock_callback,
            status_code=200,
        )

        yield project


def test_model_parameters(mock_project):
    project = mock_project

    # test get parameters without any meta parameters specified.
    mp = ModelParameters(project)
    assert ModelConfig.objects.filter(project=project).count() == 0
    assert mp.get_inputs()
    assert ModelConfig.objects.filter(project=project).count() == 1

    mp.meta_parameters_parser()
    assert ModelConfig.objects.filter(project=project).count() == 1
    mp.model_parameters_parser()
    assert ModelConfig.objects.filter(project=project).count() == 1

    mc = ModelConfig.objects.get(
        project=project, model_version="v1", meta_parameters_values={}
    )
    defaults = mp.defaults()
    assert mc.meta_parameters_values == {}
    assert mc.meta_parameters == mp.meta_parameters_parser().dump()
    assert mc.model_parameters == mp.model_parameters_parser({})
    assert {
        "model_parameters": mc.model_parameters,
        "meta_parameters": mc.meta_parameters,
    } == defaults

    # test get cached values with updates to meta parameters
    mp_values_cleaned = {"d0": [{"value": 1}], "d1": [{"value": "hello"}]}
    mp = ModelParameters(project)
    defaults = mp.defaults(mp_values_cleaned)
    assert ModelConfig.objects.filter(project=project).count() == 2

    mc = ModelConfig.objects.get(
        project=project, model_version="v1", meta_parameters_values=mp_values_cleaned
    )
    assert mc.meta_parameters_values == mp_values_cleaned
    assert mc.meta_parameters == mp.meta_parameters_parser().dump()
    assert mc.model_parameters == mp.model_parameters_parser(mp_values_cleaned)
    assert {
        "model_parameters": mc.model_parameters,
        "meta_parameters": mc.meta_parameters,
    } == defaults

    # test going back to init doesn't break cache
    defaults = mp.defaults()
    assert ModelConfig.objects.filter(project=project).count() == 2


def test_parameter_order(monkeypatch, mock_project):
    project = mock_project
    new_defaults = copy.deepcopy(Params.defaults)
    for i in range(50):
        new_defaults[f"param-{i}"] = copy.deepcopy(new_defaults["param"])

    monkeypatch.setattr(Params, "defaults", new_defaults)

    mp = ModelParameters(project=mock_project)
    mp.get_inputs()

    mc = ModelConfig.objects.get(
        project=project, model_version="v1", meta_parameters_values={}
    )

    params = Params()
    for act, exp in zip(mc.model_parameters["section"], params.dump()):
        assert act == exp, f"Expected {act} === {exp}"
