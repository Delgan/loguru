from loguru import logger
import time


def test_enqueue():
    x = []

    def sink(message):
        time.sleep(0.1)
        x.append(message)

    logger.add(sink, format="{message}", enqueue=True)
    logger.debug("Test")
    assert len(x) == 0
    time.sleep(0.2)
    assert len(x) == 1
    assert x[0] == "Test\n"


def test_enqueue_with_exception():
    x = []

    def sink(message):
        time.sleep(0.1)
        x.append(message)

    logger.add(sink, format="{message}", enqueue=True)

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("Error")

    assert len(x) == 0
    time.sleep(0.2)
    assert len(x) == 1
    lines = x[0].splitlines()

    assert lines[0] == "Error"
    assert lines[-1] == "ZeroDivisionError: division by zero"
