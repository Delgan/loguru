import pytest

from loguru._defaults import env


@pytest.mark.parametrize("value", ["test", ""])
def test_string(value, monkeypatch):
    key = "VALID_STRING"
    monkeypatch.setenv(key, value)
    assert env(key, str) == value


@pytest.mark.parametrize("value", ["y", "1", "TRUE"])
def test_bool_positive(value, monkeypatch):
    key = "VALID_BOOL_POS"
    monkeypatch.setenv(key, value)
    assert env(key, bool) is True


@pytest.mark.parametrize("value", ["NO", "0", "false"])
def test_bool_negative(value, monkeypatch):
    key = "VALID_BOOL_NEG"
    monkeypatch.setenv(key, value)
    assert env(key, bool) is False


def test_int(monkeypatch):
    key = "VALID_INT"
    monkeypatch.setenv(key, "42")
    assert env(key, int) == 42


@pytest.mark.parametrize("value", ["", "a"])
def test_invalid_int(value, monkeypatch):
    key = "INVALID_INT"
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError):
        env(key, int)


@pytest.mark.parametrize("value", ["", "a"])
def test_invalid_bool(value, monkeypatch):
    key = "INVALID_BOOL"
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError):
        env(key, bool)
