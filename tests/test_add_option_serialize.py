import json
from loguru import logger


class JsonSink:
    def __init__(self):
        self.dict = None
        self.json = None

    def write(self, message):
        self.dict = message.record
        self.json = json.loads(message)


def test_serialize():
    sink = JsonSink()
    logger.add(sink, format="{level} {message}", serialize=True)
    logger.debug("Test")
    assert sink.json["text"] == "DEBUG Test\n"
    assert sink.dict["message"] == sink.json["record"]["message"] == "Test"
    assert set(sink.dict.keys()) == set(sink.json["record"].keys())


def test_serialize_with_exception():
    sink = JsonSink()
    logger.add(sink, format="{message}", serialize=True)

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("Error")

    lines = sink.json["text"].splitlines()
    assert lines[0] == "Error"
    assert lines[-1] == "ZeroDivisionError: division by zero"
    assert bool(sink.json["record"]["exception"])


def test_serialize_not_serializable():
    sink = JsonSink()
    logger.add(sink, format="{message}", catch=False, serialize=True)
    not_serializable = object()
    logger.bind(not_serializable=not_serializable).debug("Test")
    assert sink.dict["extra"]["not_serializable"] == not_serializable
    assert bool(sink.json["record"]["extra"]["not_serializable"])
