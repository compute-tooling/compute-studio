import pytest

from django import forms

from webapp.apps.comp.fields import (
    SeparatedValueField,
    coerce_bool,
    coerce_int,
    coerce_float,
    coerce_date,
)


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


def test_coerce_date():
    exp = "2018-01-01"
    assert coerce_date("2018-01-01") == exp
    with pytest.raises(ValueError):
        assert coerce_date("abc")


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


def test_SeparatedValueField_zerodim():
    svf = SeparatedValueField(number_dims=0)
    assert svf.clean("a") == "a"

    svf = SeparatedValueField(coerce=coerce_int, number_dims=0)
    assert svf.clean("1") == 1
    # needs to be the same, not just equal
    assert svf.clean("3.0") == 3
    assert isinstance(svf.clean("3.0"), int)

    with pytest.raises(forms.ValidationError):
        svf = SeparatedValueField(coerce=coerce_float, number_dims=0)
        svf.clean("1,2,3.0")
