from loguru import logger
import pytest
import time


class NotPicklable:
    def __getstate__(self):
        raise RuntimeError("You shall not serialize me!")

    def __setstate__(self, state):
        pass


class NotUnpicklable:
    def __getstate__(self):
        return "..."

    def __setstate__(self, state):
        raise RuntimeError("You shall not de-serialize me!")


class NotWritable:
    def __init__(self, remove_record=False):
        self._remove_record = remove_record

    def write(self, message):
        if "fail" in message.record["extra"]:
            if self._remove_record:
                del message.record
            raise RuntimeError("You asked me to fail...")
        print(message, end="")


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


def test_caught_exception_without_record(capsys):
    logger.add(NotWritable(True), enqueue=True, catch=True, format="{message}")

    logger.info("It's fine")
    logger.bind(fail=True).info("Bye bye...")
    logger.info("It's fine again")
    logger.remove()

    out, err = capsys.readouterr()
    lines = err.strip().splitlines()
    assert out == "It's fine\nIt's fine again\n"
    assert lines[0] == "--- Logging error in Loguru Handler #0 ---"
    assert lines[1].startswith("Record was: None")
    assert lines[-2] == "RuntimeError: You asked me to fail..."
    assert lines[-1] == "--- End of logging error ---"


def test_caught_exception_queue_put(writer, capsys):
    logger.add(writer, enqueue=True, catch=True, format="{message}")

    logger.info("It's fine")
    logger.bind(broken=NotPicklable()).info("Bye bye...")
    logger.info("It's fine again")
    logger.remove()

    out, err = capsys.readouterr()
    lines = err.strip().splitlines()
    assert writer.read() == "It's fine\nIt's fine again\n"
    assert out == ""
    assert lines[0] == "--- Logging error in Loguru Handler #0 ---"
    assert lines[1] == "Record was: None"
    assert lines[-2] == "RuntimeError: You shall not serialize me!"
    assert lines[-1] == "--- End of logging error ---"


def test_caught_exception_queue_get(writer, capsys):
    logger.add(writer, enqueue=True, catch=True, format="{message}")

    logger.info("It's fine")
    logger.bind(broken=NotUnpicklable()).info("Bye bye...")
    logger.info("It's fine again")
    logger.remove()

    out, err = capsys.readouterr()
    lines = err.strip().splitlines()
    assert writer.read() == "It's fine\nIt's fine again\n"
    assert out == ""
    assert lines[0] == "--- Logging error in Loguru Handler #0 ---"
    assert lines[1] == "Record was: None"
    assert lines[-2] == "RuntimeError: You shall not de-serialize me!"
    assert lines[-1] == "--- End of logging error ---"


def test_caught_exception_sink_write(capsys):
    logger.add(NotWritable(), enqueue=True, catch=True, format="{message}")

    logger.info("It's fine")
    logger.bind(fail=True).info("Bye bye...")
    logger.info("It's fine again")
    logger.remove()

    out, err = capsys.readouterr()
    lines = err.strip().splitlines()
    assert out == "It's fine\nIt's fine again\n"
    assert lines[0] == "--- Logging error in Loguru Handler #0 ---"
    assert lines[1].startswith("Record was: {")
    assert lines[1].endswith("}")
    assert lines[-2] == "RuntimeError: You asked me to fail..."
    assert lines[-1] == "--- End of logging error ---"


def test_not_caught_exception_queue_put(writer, capsys):
    logger.add(writer, enqueue=True, catch=False, format="{message}")

    logger.info("It's fine")

    with pytest.raises(RuntimeError, match=r"You shall not serialize me!"):
        logger.bind(broken=NotPicklable()).info("Bye bye...")

    logger.remove()

    out, err = capsys.readouterr()
    lines = err.strip().splitlines()
    assert writer.read() == "It's fine\n"
    assert out == ""
    assert err == ""


def test_not_caught_exception_queue_get(writer, capsys):
    logger.add(writer, enqueue=True, catch=False, format="{message}")

    logger.info("It's fine")
    logger.bind(broken=NotUnpicklable()).info("Bye bye...")
    logger.info("It's not fine")
    logger.remove()

    out, err = capsys.readouterr()
    lines = err.strip().splitlines()
    assert writer.read() == "It's fine\n"
    assert out == ""
    assert lines[0].startswith("Exception")
    assert lines[-1] == "RuntimeError: You shall not de-serialize me!"


def test_not_caught_exception_sink_write(capsys):
    logger.add(NotWritable(), enqueue=True, catch=False, format="{message}")

    logger.info("It's fine")
    logger.bind(fail=True).info("Bye bye...")
    logger.info("It's not fine")
    logger.remove()

    out, err = capsys.readouterr()
    lines = err.strip().splitlines()
    assert out == "It's fine\n"
    assert lines[0].startswith("Exception")
    assert lines[-1] == "RuntimeError: You asked me to fail..."
