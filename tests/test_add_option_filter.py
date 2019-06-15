import pytest
from loguru import logger


@pytest.mark.parametrize(
    "filter",
    [
        None,
        "",
        "tests",
        "tests.test_add_option_filter",
        (lambda r: True),
        (lambda r: r["level"] == "DEBUG"),
    ],
)
def test_filterd_in(filter, writer):
    logger.add(writer, filter=filter, format="{message}")
    logger.debug("Test Filter")
    assert writer.read() == "Test Filter\n"


@pytest.mark.parametrize(
    "filter",
    [
        "test",
        "testss",
        "tests.",
        "tests.test_add_option_filter.",
        ".",
        (lambda r: False),
        (lambda r: r["level"].no != 10),
    ],
)
def test_filtered_out(filter, writer):
    logger.add(writer, filter=filter, format="{message}")
    logger.debug("Test Filter")
    assert writer.read() == ""


@pytest.mark.parametrize("filter", ["tests", "", lambda _: False])
def test_filtered_out_f_globals_name_absent(writer, filter, f_globals_name_absent):
    logger.add(writer, filter=filter, format="{message}")
    logger.info("It's not ok")
    assert writer.read() == ""


@pytest.mark.parametrize("filter", [None, lambda _: True])
def test_filtered_in_f_globals_name_absent(writer, filter, f_globals_name_absent):
    logger.add(writer, filter=filter, format="{message}")
    logger.info("It's ok")
    assert writer.read() == "It's ok\n"


@pytest.mark.parametrize("filter", [-1, 3.4, object()])
def test_invalid_filter(writer, filter):
    with pytest.raises(ValueError):
        logger.add(writer, filter=filter)
