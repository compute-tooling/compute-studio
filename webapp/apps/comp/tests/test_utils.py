import json

import pytest

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
