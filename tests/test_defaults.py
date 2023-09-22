import pytest

from loguru._defaults import env


@pytest.mark.parametrize("value", ["test", ""])
def test_string(value, monkeypatch):
    with monkeypatch.context() as context:
        key = "VALID_STRING"
        context.setenv(key, value)
        assert env(key, str) == value


@pytest.mark.parametrize("value", ["y", "1", "TRUE"])
def test_bool_positive(value, monkeypatch):
    with monkeypatch.context() as context:
        key = "VALID_BOOL_POS"
        context.setenv(key, value)
        assert env(key, bool) is True


@pytest.mark.parametrize("value", ["NO", "0", "false"])
def test_bool_negative(value, monkeypatch):
    with monkeypatch.context() as context:
        key = "VALID_BOOL_NEG"
        context.setenv(key, value)
        assert env(key, bool) is False


def test_int(monkeypatch):
    with monkeypatch.context() as context:
        key = "VALID_INT"
        context.setenv(key, "42")
        assert env(key, int) == 42


@pytest.mark.parametrize("value", ["", "a"])
def test_invalid_int(value, monkeypatch):
    with monkeypatch.context() as context:
        key = "INVALID_INT"
        context.setenv(key, value)
        with pytest.raises(ValueError):
            env(key, int)


@pytest.mark.parametrize("value", ["", "a"])
def test_invalid_bool(value, monkeypatch):
    with monkeypatch.context() as context:
        key = "INVALID_BOOL"
        context.setenv(key, value)
        with pytest.raises(ValueError):
            env(key, bool)
