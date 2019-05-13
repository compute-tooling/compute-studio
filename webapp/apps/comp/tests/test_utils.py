import json

import pytest
import paramtools

from webapp.apps.comp.utils import (
    is_reverse,
    is_wildcard,
    json_int_key_encode,
    match_unknown_field,
)
from webapp.apps.comp.exceptions import MatchFailedError


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


def test_unknown_field():
    form_fields = ["hello", "world", "hello_checkbox"]
    flat_defaults = {"hello": {"title": "Hello"}, "world": {"title": "World"}}

    anchor_id, title = match_unknown_field("_ello", flat_defaults, form_fields)

    assert anchor_id == "#id_hello"
    assert title == "Hello"

    anchor_id, title = match_unknown_field("_ello_checkbox", flat_defaults, form_fields)

    assert anchor_id == "#label-id_hello_checkbox"
    assert title == "Hello"

    with pytest.raises(MatchFailedError):
        match_unknown_field("notclose", flat_defaults, form_fields)
