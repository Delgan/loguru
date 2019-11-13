import logging


class StreamSink:
    def __init__(self, stream):
        self._stream = stream
        self._flushable = hasattr(stream, "flush") and callable(stream.flush)
        self._stoppable = hasattr(stream, "stop") and callable(stream.stop)

    def write(self, message):
        self._stream.write(message)
        if self._flushable:
            self._stream.flush()

    def stop(self):
        if self._stoppable:
            self._stream.stop()


class StandardSink:
    def __init__(self, handler):
        self._handler = handler
        self._root_logger = logging.getLogger()

    def write(self, message):
        record = message.record
        message = str(message)
        exc = record["exception"]
        record = self._root_logger.makeRecord(
            record["name"],
            record["level"].no,
            record["file"].path,
            record["line"],
            message,
            (),
            (exc.type, exc.value, exc.traceback) if exc else None,
            record["function"],
            record["extra"],
        )
        if exc:
            record.exc_text = "\n"
        self._handler.handle(record)

    def stop(self):
        self._handler.close()


class CallableSink:
    def __init__(self, function):
        self._function = function

    def write(self, message):
        self._function(message)

    def stop(self):
        pass
