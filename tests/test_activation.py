import pytest
from loguru import logger


@pytest.mark.parametrize(
    "name, should_log",
    [
        ("", False),
        ("tests", False),
        ("test", True),
        ("testss", True),
        ("tests.", True),
        ("tests.test_activation", False),
        ("tests.test_activation.", True),
        ("test_activation", True),
        (".", True),
    ],
)
def test_disable(writer, name, should_log):
    logger.add(writer, format="{message}")
    logger.disable(name)
    logger.debug("message")
    result = writer.read()

    if should_log:
        assert result == "message\n"
    else:
        assert result == ""


@pytest.mark.parametrize(
    "name, should_log",
    [
        ("", True),
        ("tests", True),
        ("test", False),
        ("testss", False),
        ("tests.", False),
        ("tests.test_activation", True),
        ("tests.test_activation.", False),
        ("test_activation", False),
        (".", False),
    ],
)
def test_enable(writer, name, should_log):
    logger.add(writer, format="{message}")
    logger.disable("")
    logger.enable(name)
    logger.debug("message")
    result = writer.read()

    if should_log:
        assert result == "message\n"
    else:
        assert result == ""


def test_log_before_enable(writer):
    logger.add(writer, format="{message}")
    logger.disable("")
    logger.debug("nope")
    logger.enable("tests")
    logger.debug("yes")
    result = writer.read()
    assert result == "yes\n"


def test_log_before_disable(writer):
    logger.add(writer, format="{message}")
    logger.enable("")
    logger.debug("yes")
    logger.disable("tests")
    logger.debug("nope")
    result = writer.read()
    assert result == "yes\n"


def test_multiple_activations():
    n = lambda: len(logger._activation_list)

    assert n() == 0
    logger.enable("")
    assert n() == 0
    logger.disable("")
    assert n() == 1
    logger.enable("foo")
    assert n() == 2
    logger.enable("foo.bar")
    assert n() == 2
    logger.disable("foo")
    assert n() == 1
    logger.disable("foo.bar")
    assert n() == 1
    logger.enable("foo.bar")
    assert n() == 2
    logger.disable("foo.bar.baz")
    assert n() == 3
    logger.disable("foo.baz")
    assert n() == 3
    logger.disable("foo.baz.bar")
    assert n() == 3
    logger.enable("foo.baz.bar")
    assert n() == 4
    logger.enable("")
    assert n() == 0


@pytest.mark.parametrize("name", [42, [], object(), None])
def test_invalid_enable_name(name):
    with pytest.raises(ValueError):
        logger.enable(name)


@pytest.mark.parametrize("name", [42, [], object(), None])
def test_invalid_disable_name(name):
    with pytest.raises(ValueError):
        logger.disable(name)
