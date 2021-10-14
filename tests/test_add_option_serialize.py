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


def custom_serializer(text: any, record: object) -> str:
    """
    Custom serializer
    """
    exception = record["exception"]

    if exception is not None:
        exception = {
            "type": None if exception.type is None else exception.type.__name__,
            "value": exception.value,
            "traceback": bool(record["exception"].traceback),
        }

    serializable = {
        "message": text,
        "level": record["level"].name,
        "record": {
            "elapsed": {
                "repr": record["elapsed"],
                "seconds": record["elapsed"].total_seconds(),
            },
            "exception": exception,
            "extra": record["extra"],
            "file": {"name": record["file"].name, "path": record["file"].path},
            "function": record["function"],
            "level": {
                "icon": record["level"].icon,
                "name": record["level"].name,
                "no": record["level"].no,
            },
            "line": record["line"],
            "message": record["message"],
            "module": record["module"],
            "name": record["name"],
            "process": {"id": record["process"].id, "name": record["process"].name},
            "thread": {"id": record["thread"].id, "name": record["thread"].name},
            "time": {"repr": record["time"], "timestamp": record["time"].timestamp()},
        },
    }

    return json.dumps(serializable, default=str) + "\n"


def test_serialize():
    sink = JsonSink()
    logger.add(sink, format="{level} {message}", serialize=True)
    logger.debug("Test")
    assert sink.json["text"] == "DEBUG Test\n"
    assert sink.dict["message"] == sink.json["record"]["message"] == "Test"
    assert set(sink.dict.keys()) == set(sink.json["record"].keys())


def test_serialize_via_serializer():
    sink = JsonSink()
    logger.add(sink, format="{level} {message}", serialize=True, serializer= custom_serializer)
    logger.debug("Test")
    assert sink.json["message"] == "DEBUG Test\n"
    assert sink.json["level"] == "DEBUG"
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
