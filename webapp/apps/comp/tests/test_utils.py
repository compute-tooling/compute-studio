import json

import pytest
import paramtools

from webapp.apps.comp.utils import is_reverse, is_wildcard, json_int_key_encode


@pytest.mark.parametrize(
    "item,exp", [("<", True), ("a", False), ("1", False), (1, False), (False, False)]
)
def test_is_reverse(item, exp):
    assert is_reverse(item) is exp


@pytest.mark.parametrize(
    "item,exp", [("*", True), ("a", False), ("1", False), (1, False), (False, False)]
)
def test_is_wildcard(item, exp):
    assert is_wildcard(item) is exp


def test_json_int_key_encode():
    exp = {2017: "stuff", 2019: {2016: "stuff", 2000: {1: "heyo"}}}
    json_str = json.loads(json.dumps(exp))
    act = json_int_key_encode(json_str)
    assert exp == act


# def test_param_naming(TestParams: Parameters, pt_metaparam: dict):
#     class TestParams(paramtools.Parameters):
#         defaults = {

#         }

#     raw_meta_params = {"dim0": "zero"}
#     mp_inst = pt_metaparam.validate(raw_meta_params)
#     params = TestParams()
#     spec = params.specification(meta_data=True, **mp_inst)

#     pname = "min_int_param"
#     fake_vi = {"dim0": "one", "dim1": "heyo", "dim2": "byo", "value": 123}
#     param = Param(pname, spec[pname], **mp_inst)
#     newname, suffix = dims_to_string(pname, fake_vi, mp_inst)
#     assert suffix == "dim0__mp___dim1__heyo___dim2__byo"
#     assert newname == pname + "____" + suffix

#     param.set_fields([fake_vi])
#     exp = "min_int_param____dim0__mp___dim1__heyo___dim2__byo"
#     assert param.col_fields[-1].name == exp
#     assert param.col_fields[-1].default_value == 123
#     assert exp in param.fields

#     pname = "min_int_param"
#     fake_vi = {"value": 123}
#     param = Param(pname, spec[pname], **mp_inst)
#     newname, suffix = dims_to_string(pname, fake_vi, mp_inst)
#     assert suffix == ""
#     assert newname == pname
