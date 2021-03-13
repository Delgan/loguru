import pytest

from loguru import logger


def test_bind_after_add(writer):
    logger.add(writer, format="{extra[a]} {message}")
    logger_bound = logger.bind(a=0)
    logger_bound.debug("A")

    assert writer.read() == "0 A\n"


def test_bind_before_add(writer):
    logger_bound = logger.bind(a=0)
    logger.add(writer, format="{extra[a]} {message}")
    logger_bound.debug("A")

    assert writer.read() == "0 A\n"


def test_add_using_bound(writer):
    logger.configure(extra={"a": -1})
    logger_bound = logger.bind(a=0)
    logger_bound.add(writer, format="{extra[a]} {message}")
    logger.debug("A")
    logger_bound.debug("B")

    assert writer.read() == "-1 A\n0 B\n"


def test_not_override_parent_logger(writer):
    logger_1 = logger.bind(a="a")
    logger_2 = logger_1.bind(a="A")
    logger.add(writer, format="{extra[a]} {message}")

    logger_1.debug("1")
    logger_2.debug("2")

    assert writer.read() == "a 1\nA 2\n"


def test_override_previous_bound(writer):
    logger.add(writer, format="{extra[x]} {message}")
    logger.bind(x=1).bind(x=2).debug("3")
    assert writer.read() == "2 3\n"


def test_no_conflict(writer):
    logger_ = logger.bind()
    logger_2 = logger_.bind(a=2)
    logger_3 = logger_.bind(a=3)

    logger.add(writer, format="{extra[a]} {message}")

    logger_2.debug("222")
    logger_3.debug("333")

    assert writer.read() == "2 222\n3 333\n"


@pytest.mark.parametrize("using_bound", [True, False])
def test_bind_and_add_level(writer, using_bound):
    logger_bound = logger.bind()
    logger.add(writer, format="{level.name} {message}")

    if using_bound:
        logger_bound.level("bar", 15)
    else:
        logger.level("bar", 15)

    logger.log("bar", "root")
    logger_bound.log("bar", "bound")

    assert writer.read() == "bar root\nbar bound\n"


def test_override_configured(writer):
    logger.configure(extra={"a": 1})
    logger2 = logger.bind(a=2)

    logger2.add(writer, format="{extra[a]} {message}")

    logger2.debug("?")

    assert writer.read() == "2 ?\n"
