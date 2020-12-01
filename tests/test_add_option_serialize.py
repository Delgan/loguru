import csv
import io
import json
import sys
from loguru import logger


class JsonSink:
    def __init__(self):
        self.dict = None
        self.json = None

    def write(self, message):
        self.dict = message.record
        self.json = json.loads(message)


class CSVSink:
    def __init__(self):
        self.dict = None
        self.csv = None

    def write(self, message):
        self.dict = message.record
        keys = ["text", "elapsed", "message", "filename", "time"]
        temp_io = io.StringIO(message)
        self.csv = [a for a in csv.DictReader(temp_io, keys)][0]


def test_serialize_to_csv():
    keys = ["text", "elapsed", "message", "filename", "time"]

    def serializer(message, default):
        temp_io = io.StringIO()
        writer = csv.DictWriter(temp_io, keys)
        msg = {
            "text": message["text"].strip(),
            "message": message["record"]["message"],
            "elapsed": message["record"]["elapsed"]["seconds"],
            "filename": message["record"]["file"]["name"],
        }

        writer.writerows([msg])
        temp_io.seek(0)
        return temp_io.read()

    sink = CSVSink()
    logger.add(sink, format="{level} {message}", serialize=serializer)
    logger.debug("Test")
    assert sink.csv["text"] == "DEBUG Test"
    assert sink.dict["message"] == sink.csv["message"]
    assert not set(sink.csv.keys()).difference(keys)


def test_serialize():
    sink = JsonSink()
    logger.add(sink, format="{level} {message}", serialize=True)
    logger.debug("Test")
    assert sink.json["text"] == "DEBUG Test\n"
    assert sink.dict["message"] == sink.json["record"]["message"] == "Test"
    assert set(sink.dict.keys()) == set(sink.json["record"].keys())


def test_serialize_exception():
    sink = JsonSink()
    logger.add(sink, format="{message}", serialize=True, catch=False)

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("Error")

    lines = sink.json["text"].splitlines()
    assert lines[0] == "Error"
    assert lines[-1] == "ZeroDivisionError: division by zero"

    assert sink.json["record"]["exception"] == {
        "type": "ZeroDivisionError",
        "value": "division by zero",
        "traceback": True,
    }


def test_serialize_exception_without_context():
    sink = JsonSink()
    logger.add(sink, format="{message}", serialize=True, catch=False)

    logger.exception("No Error")

    lines = sink.json["text"].splitlines()
    assert lines[0] == "No Error"
    assert lines[-1] == "NoneType" if sys.version_info < (3, 5, 3) else "NoneType: None"

    assert sink.json["record"]["exception"] == {
        "type": None,
        "value": None,
        "traceback": False,
    }


def test_serialize_exception_none_tuple():
    sink = JsonSink()
    logger.add(sink, format="{message}", serialize=True, catch=False)

    logger.opt(exception=(None, None, None)).error("No Error")

    lines = sink.json["text"].splitlines()
    assert lines[0] == "No Error"
    assert lines[-1] == "NoneType" if sys.version_info < (3, 5, 3) else "NoneType: None"

    assert sink.json["record"]["exception"] == {
        "type": None,
        "value": None,
        "traceback": False,
    }


def test_serialize_exception_instrance():
    sink = JsonSink()
    logger.add(sink, format="{message}", serialize=True, catch=False)

    logger.opt(exception=ZeroDivisionError("Oops")).error("Failure")

    lines = sink.json["text"].splitlines()
    assert lines[0] == "Failure"
    assert lines[-1] == "ZeroDivisionError: Oops"

    assert sink.json["record"]["exception"] == {
        "type": "ZeroDivisionError",
        "value": "Oops",
        "traceback": False,
    }


def test_serialize_with_catch_decorator():
    sink = JsonSink()
    logger.add(sink, format="{message}", serialize=True, catch=False)

    @logger.catch
    def foo():
        1 / 0

    foo()

    lines = sink.json["text"].splitlines()
    assert lines[0].startswith("An error has been caught")
    assert lines[-1] == "ZeroDivisionError: division by zero"
    assert bool(sink.json["record"]["exception"])


def test_serialize_with_record_option():
    sink = JsonSink()
    logger.add(sink, format="{message}", serialize=True, catch=False)

    logger.opt(record=True).info("Test", foo=123)

    assert sink.json["text"] == "Test\n"
    assert sink.dict["extra"] == {"foo": 123}


def test_serialize_not_serializable():
    sink = JsonSink()
    logger.add(sink, format="{message}", catch=False, serialize=True)
    not_serializable = object()
    logger.bind(not_serializable=not_serializable).debug("Test")
    assert sink.dict["extra"]["not_serializable"] == not_serializable
    assert bool(sink.json["record"]["extra"]["not_serializable"])
