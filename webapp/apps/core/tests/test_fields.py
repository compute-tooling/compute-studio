import pytest
from webapp.apps.core.fields import (SeparatedValueField, coerce_bool,
                                     coerce_int, coerce_float)


def test_coerce_bool():
    assert coerce_bool("True") is True
    assert coerce_bool("False") is False


def test_coerce_int():
    assert coerce_int("1") == 1
    assert coerce_int("2.0") == 2 and isinstance(coerce_int("2.0"), int)
    assert coerce_int(3) == 3
    assert coerce_int(2.0) == 2 and isinstance(coerce_int(2.0), int)
    with pytest.raises(ValueError):
        assert coerce_int("abc")


def test_coerce_float():
    assert coerce_float("1") == 1.0 and isinstance(coerce_float("1"), float)
    assert coerce_float("2.0") == 2.0
    assert coerce_float(3) == 3.0 and isinstance(coerce_float(3), float)
    assert coerce_float(2.0) == 2.0
    with pytest.raises(ValueError):
        assert coerce_float("abc")


def test_SeparatedValueField():
    svf = SeparatedValueField()
    assert svf.clean("a") == ["a"]
    assert svf.clean("a,b,c") == ["a", "b", "c"]

    svf = SeparatedValueField(coerce=coerce_int)
    assert svf.clean("1") == [1]
    assert svf.clean("1,2,3") == [1, 2, 3]
    # needs to be the same, not just equal
    assert svf.clean("1,2,3.0") == [1, 2, 3]
    assert all(isinstance(x, int) for x in svf.clean("1,2,3.0"))

    svf = SeparatedValueField(coerce=coerce_float)
    assert svf.clean("1") == [1]
    assert svf.clean("1,2,3") == [1, 2, 3]
    # needs to be the same, not just equal
    assert svf.clean("1,2,3.0") == [1, 2, 3]
    assert all(isinstance(x, float) for x in svf.clean("1,2,3.0"))
