import pytest

from loguru import logger


@pytest.mark.parametrize("raw,original,replacement", (
    (False, "\n", "\\n"),
    (False, "\r", "\\r"),
    (True, "\n", "\n"),
    (True, "\r", "\r"),
))
def test_clrf(writer, raw, original, replacement):
    logger.add(writer, format="{message}")
    logger.opt(raw=raw).debug(f"Line{original}Next line")
    assert writer.read() == f"Line{replacement}Next line" + ("\n" if not raw else "")
