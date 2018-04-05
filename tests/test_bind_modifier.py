import pytest
from loguru import logger

def test_bind_after_start(writer):
    def modifier(extra):
        extra["abc"] = 321

    logger.start(writer, format="{extra[abc]} {message}")
    logger_ = logger.bind_modifier(modifier)
    logger_.debug("Modified")

    assert writer.read() == "321 Modified\n"

def test_bind_before_start(writer):
    def modifier(extra):
        extra["cba"] = 123

    logger_ = logger.bind_modifier(modifier)
    logger.start(writer, format="{extra[cba]} {message}")
    logger_.debug("Modified")

    assert writer.read() == "123 Modified\n"

def test_not_override_parent_logger(writer):
    def modifier(extra):
        extra["a"] = 2

    logger2 = logger.bind(a=1)
    logger3 = logger2.bind_modifier(modifier)

    logger.start(writer, format="{extra[a]} {message}")

    logger2.debug("A")
    logger3.debug("B")

    assert writer.read() == "1 A\n2 B\n"

def test_modify_bound_extra(writer):
    def modifier(extra):
        extra["pre"] += 10

    logger.start(writer, format="{extra[pre]} {message}")

    logger.bind(pre=1).bind_modifier(modifier).debug("OK")

    assert writer.read() == "11 OK\n"

def test_multiple_binds(writer):
    def modifier_1(extra):
        extra["a"] = "A"

    def modifier_2(extra):
        extra["b"] = "B"

    logger.start(writer, format="{extra[a]} {extra[b]} {message}")

    logger.bind_modifier(modifier_1).bind_modifier(modifier_2).debug("C")

    assert writer.read() == "A B C\n"

def test_multiple_binds_order(writer):
    def first_modifier(extra):
        extra["A"] = 15

    def second_modifier(extra):
        extra["A"] += 10

    logger.start(writer, format="{extra[A]} {message}")

    logger.bind_modifier(first_modifier).bind_modifier(second_modifier).debug("@")

    assert writer.read() == "25 @\n"

def test_multiple_no_conflict(writer):
    def modifier_1(extra):
        extra["a"] += 1

    def modifier_2(extra):
        extra["a"] += 2

    logger_ = logger.bind(a=0)
    logger_1 = logger_.bind_modifier(modifier_1)
    logger_2 = logger_.bind_modifier(modifier_2)

    logger.start(writer, format="{extra[a]} {message}")

    logger_1.debug("A")
    logger_2.debug("B")

    assert writer.read() == "1 A\n2 B\n"

def test_override_configured(writer):
    def modifier_root(extra):
        extra["a"] = "A"
        extra["b"] = "B"

    def modifier(extra):
        extra["a"] = "a"

    logger.configure(modifier=modifier_root)
    logger_ = logger.bind_modifier(modifier)

    logger.start(writer, format="{extra[a]} {extra[b]} {message}")

    logger_.debug("!")

    assert writer.read() == "a B !\n"

@pytest.mark.parametrize("modifier", [object(), 1, None, {"a": 1}])
def test_invalid_modifier(writer, modifier):
    with pytest.raises(ValueError):
        logger.bind_modifier(modifier)
