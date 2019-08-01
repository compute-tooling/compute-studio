import json

import pytest
import paramtools

from webapp.apps.comp.utils import json_int_key_encode


def test_json_int_key_encode():
    exp = {2017: "stuff", 2019: {2016: "stuff", 2000: {1: "heyo"}}}
    json_str = json.loads(json.dumps(exp))
    act = json_int_key_encode(json_str)
    assert exp == act
