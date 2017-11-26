import pytest
import importlib
import loguru
import sys
import os

def reload():
    importlib.reload(loguru._constants)
    importlib.reload(loguru._logger)
    importlib.reload(loguru)

@pytest.fixture
def logenv():
    env = os.environ.copy()

    def logenv(key, value):
        os.environ[str(key)] = str(value)
        reload()
        return loguru.logger

    yield logenv

    os.environ.clear()
    os.environ.update(env)
    reload()

def test_autoinit(capsys, logenv):
    logger = logenv("LOGURU_AUTOINIT", 0)
    logger.warning("Nope")
    out, err = capsys.readouterr()
    assert out == err == ""

def test_format(capsys, logenv):
    logger = logenv("LOGURU_FORMAT", "a => {message} => b")
    logger.debug("YES")
    out, err = capsys.readouterr()
    assert out == ""
    assert err == "a => YES => b\n"

def test_level(capsys, logenv):
    logger = logenv("LOGURU_LEVEL", "ERROR")
    logger.warning("nope")
    out, err = capsys.readouterr()
    assert out == err == ""
    logger.error("yes")
    out, err = capsys.readouterr()
    assert out == ""
    assert err != ""

def test_colored(capsys, logenv):
    logger = logenv("LOGURU_COLORED", False)
    logger.start(sys.stdout, format="<red>{message}</red>")
    logger.debug("message")
    out, _ = capsys.readouterr()
    assert out == "message\n"

def test_structured(capsys, logenv):
    logger = logenv("LOGURU_STRUCTURED", "YES")
    logger.debug("message")
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith("{")
    assert err.endswith("}\n")

def test_enhanced(capsys, logenv):
    logger = logenv("LOGURU_ENHANCED", "y")
    logger.start(sys.stdout, enhanced=False)
    try:
        a, b = 1, 0
        a / b
    except ZeroDivisionError:
        logger.exception("error...")
    out, err = capsys.readouterr()
    assert len(err) > len(out)

def test_level_no(capsys, logenv):
    logger = logenv("LOGURU_DEBUG_NO", 14)
    logger.start(sys.stdout, format="{level.no}")
    logger.debug("?")
    out, _ = capsys.readouterr()
    assert out == "14\n"

def test_level_color(capsys, logenv):
    logger = logenv("LOGURU_INFO_COLOR", "<red>")
    logger.start(sys.stdout, format="<level>{message}</level>", colored=True)
    logger.info(" ? ")
    out, _ = capsys.readouterr()
    assert out == "\x1b[31m ? \x1b[0m\n"

def test_level_icon(capsys, logenv):
    logger = logenv("LOGURU_ERROR_ICON", "@")
    logger.start(sys.stdout, format="{message} + {level.icon}")
    logger.error("msg")
    out, _ = capsys.readouterr()
    assert out == "msg + @\n"

@pytest.mark.parametrize("value", ["", "a"])
def test_invalid_int(value, logenv):
    with pytest.raises(ValueError):
        logenv("LOGURU_DEBUG_NO", value)

@pytest.mark.parametrize("value", ["", "a"])
def test_invalid_bool(value, logenv):
    with pytest.raises(ValueError):
        logenv("LOGURU_AUTOINIT", value)
