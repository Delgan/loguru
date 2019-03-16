from collections import namedtuple


class LevelRecattr(str):
    __slots__ = ("name", "no", "icon")


class FileRecattr(str):
    __slots__ = ("name", "path")


class ThreadRecattr(str):
    __slots__ = ("name", "id")


class ProcessRecattr(str):
    __slots__ = ("name", "id")


class ExceptionRecattr(namedtuple("ExceptionRecattr", ("type", "value", "traceback"))):
    def __reduce__(self):
        exception = (self.type, self.value, None)  # tracebacks are not pickable
        return (ExceptionRecattr, exception)
