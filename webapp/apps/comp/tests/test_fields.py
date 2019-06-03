import pytest

from django import forms

from webapp.apps.comp.fields import (
    ValueField,
    ChoiceValueField,
    DataList,
    coerce_bool,
    coerce_int,
    coerce_float,
    coerce_date,
    coerce,
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


def test_ValueField():
    svf = ValueField()
    assert svf.clean("a") == ["a"]
    assert svf.clean("a,b,c") == ["a", "b", "c"]

    svf = ValueField(coerce=coerce_int)
    assert svf.clean("1") == [1]
    assert svf.clean("1,2,3") == [1, 2, 3]
    # needs to be the same, not just equal
    assert svf.clean("1,2,3.0") == [1, 2, 3]
    assert all(isinstance(x, int) for x in svf.clean("1,2,3.0"))

    svf = ValueField(coerce=coerce_float)
    assert svf.clean("1") == [1]
    assert svf.clean("1,2,3") == [1, 2, 3]
    # needs to be the same, not just equal
    assert svf.clean("1,2,3.0") == [1, 2, 3]
    assert all(isinstance(x, float) for x in svf.clean("1,2,3.0"))


def test_ValueField_zerodim():
    svf = ValueField(number_dims=0)
    assert svf.clean("a") == "a"

    svf = ValueField(coerce=coerce_int, number_dims=0)
    assert svf.clean("1") == 1
    # needs to be the same, not just equal
    assert svf.clean("3.0") == 3
    assert isinstance(svf.clean("3.0"), int)

    assert svf.clean("1,2,3.0") == [1, 2, 3]

    assert svf.clean("<,1,*") == ["<", 1, "*"]
    assert svf.clean("<") == ["<"]
    assert svf.clean("*") == ["*"]


def test_ChoiceValueField():
    cvf = ChoiceValueField(
        [(True, True), (False, False)], coerce=coerce_bool, number_dims=0
    )
    assert cvf.clean("True") == True
    assert cvf.clean("True,*,*,False") == [True, "*", "*", False]

    cvf = ChoiceValueField(
        [("hello", "hello"), ("world", "world")], coerce=coerce, number_dims=0
    )
    assert cvf.clean("hello") == "hello"
    assert cvf.clean("<,hello,world") == ["<", "hello", "world"]
    with pytest.raises(forms.ValidationError) as e:
        cvf.clean("yep,bad input")
