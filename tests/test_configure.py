import sys

import pytest

from loguru import logger


def test_handlers(capsys, tmpdir):
    file = tmpdir.join("test.log")

    handlers = [
        {"sink": str(file), "format": "FileSink: {message}"},
        {"sink": sys.stdout, "format": "StdoutSink: {message}"},
    ]

    logger.configure(handlers=handlers)
    logger.debug("test")

    out, err = capsys.readouterr()

    assert file.read() == "FileSink: test\n"
    assert out == "StdoutSink: test\n"
    assert err == ""


def test_levels(writer):
    levels = [{"name": "my_level", "icon": "X", "no": 12}, {"name": "DEBUG", "icon": "!"}]

    logger.add(writer, format="{level.no}|{level.name}|{level.icon}|{message}")
    logger.configure(levels=levels)

    logger.log("my_level", "test")
    logger.debug("no bug")

    assert writer.read() == ("12|my_level|X|test\n" "10|DEBUG|!|no bug\n")


def test_extra(writer):
    extra = {"a": 1, "b": 9}

    logger.add(writer, format="{extra[a]} {extra[b]}")
    logger.configure(extra=extra)

    logger.debug("")

    assert writer.read() == "1 9\n"


def test_patcher(writer):
    logger.add(writer, format="{extra[a]} {extra[b]}")
    logger.configure(patcher=lambda record: record["extra"].update(a=1, b=2))

    logger.debug("")

    assert writer.read() == "1 2\n"


def test_activation(writer):
    activation = [("tests", False), ("tests.test_configure", True)]

    logger.add(writer, format="{message}")
    logger.configure(activation=activation)

    logger.debug("Logging")

    assert writer.read() == "Logging\n"


def test_dict_unpacking(writer):
    config = {
        "handlers": [{"sink": writer, "format": "{level.no} - {extra[x]} {extra[z]} - {message}"}],
        "levels": [{"name": "test", "no": 30}],
        "extra": {"x": 1, "y": 2, "z": 3},
    }

    logger.debug("NOPE")

    logger.configure(**config)

    logger.log("test", "Yes!")

    assert writer.read() == "30 - 1 3 - Yes!\n"


def test_returned_ids(capsys):
    ids = logger.configure(
        handlers=[
            {"sink": sys.stdout, "format": "{message}"},
            {"sink": sys.stderr, "format": "{message}"},
        ]
    )

    assert len(ids) == 2

    logger.debug("Test")

    out, err = capsys.readouterr()

    assert out == "Test\n"
    assert err == "Test\n"

    for i in ids:
        logger.remove(i)

    logger.debug("Nope")

    out, err = capsys.readouterr()

    assert out == ""
    assert err == ""


def test_dont_reset_by_default(writer):
    logger.configure(extra={"a": 1}, patcher=lambda r: r["extra"].update(b=2))
    logger.level("b", no=30)
    logger.add(writer, format="{level} {extra[a]} {extra[b]} {message}")

    logger.configure()

    logger.log("b", "Test")

    assert writer.read() == "b 1 2 Test\n"


def test_reset_previous_handlers(writer):
    logger.add(writer, format="{message}")

    logger.configure(handlers=[])

    logger.debug("Test")

    assert writer.read() == ""


def test_reset_previous_extra(writer):
    logger.configure(extra={"a": 123})
    logger.add(writer, format="{extra[a]}", catch=False)

    logger.configure(extra={})

    with pytest.raises(KeyError):
        logger.debug("Nope")


def test_reset_previous_patcher(writer):
    logger.configure(patcher=lambda r: r.update(a=123))
    logger.add(writer, format="{extra[a]}", catch=False)

    logger.configure(patcher=lambda r: None)

    with pytest.raises(KeyError):
        logger.debug("Nope")


def test_dont_reset_previous_levels(writer):
    logger.level("abc", no=30)

    logger.configure(levels=[])

    logger.add(writer, format="{level} {message}")

    logger.log("abc", "Test")

    assert writer.read() == "abc Test\n"


def test_configure_handler_using_new_level(writer):
    logger.configure(
        levels=[{"name": "CONF_LVL", "no": 33, "icon": "", "color": ""}],
        handlers=[
            {"sink": writer, "level": "CONF_LVL", "format": "{level.name} {level.no} {message}"}
        ],
    )

    logger.log("CONF_LVL", "Custom")
    assert writer.read() == "CONF_LVL 33 Custom\n"


def test_configure_filter_using_new_level(writer):
    logger.configure(
        levels=[{"name": "CONF_LVL_2", "no": 33, "icon": "", "color": ""}],
        handlers=[
            {"sink": writer, "level": 0, "filter": {"tests": "CONF_LVL_2"}, "format": "{message}"}
        ],
    )

    logger.log("CONF_LVL_2", "Custom")
    assert writer.read() == "Custom\n"


def test_configure_before_bind(writer):
    logger.configure(extra={"a": "default_a", "b": "default_b"})
    logger.add(writer, format="{extra[a]} {extra[b]} {message}")

    logger.debug("init")

    logger_a = logger.bind(a="A")
    logger_b = logger.bind(b="B")

    logger_a.debug("aaa")
    logger_b.debug("bbb")

    assert writer.read() == ("default_a default_b init\n" "A default_b aaa\n" "default_a B bbb\n")


def test_configure_after_bind(writer):
    logger_a = logger.bind(a="A")
    logger_b = logger.bind(b="B")

    logger.configure(extra={"a": "default_a", "b": "default_b"})
    logger.add(writer, format="{extra[a]} {extra[b]} {message}")

    logger.debug("init")

    logger_a.debug("aaa")
    logger_b.debug("bbb")

    assert writer.read() == ("default_a default_b init\n" "A default_b aaa\n" "default_a B bbb\n")
