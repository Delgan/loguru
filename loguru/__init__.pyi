"""
.. |str| replace:: :class:`str`
.. |namedtuple| replace:: :func:`namedtuple<collections.namedtuple>`
.. |dict| replace:: :class:`dict`

.. |Logger| replace:: :class:`~loguru._logger.Logger`
.. |catch| replace:: :meth:`~loguru._logger.Logger.catch()`
.. |bind| replace:: :meth:`~loguru._logger.Logger.bind()`
.. |patch| replace:: :meth:`~loguru._logger.Logger.patch()`
.. |opt| replace:: :meth:`~loguru._logger.Logger.opt()`
.. |level| replace:: :meth:`~loguru._logger.Logger.level()`

.. _stub file: https://www.python.org/dev/peps/pep-0484/#stub-files
.. _string literals: https://www.python.org/dev/peps/pep-0484/#forward-references
.. _postponed evaluation of annotations: https://www.python.org/dev/peps/pep-0563/
.. |future| replace:: ``__future__``
.. _future: https://www.python.org/dev/peps/pep-0563/#enabling-the-future-behavior-in-python-3-7

Loguru relies on a `stub file`_ to document its types. This implies that these types are not
accessible during execution of your program, however they can be used by type checkers and IDE.
Also, this means that your Python interpreter has to support `postponed evaluation of annotations`_
to prevent error at runtime. This is achieved with a |future|_ import in Python 3.7 or by using
`string literals`_ for earlier versions.

A basic usage example could look like this:

.. code-block:: python

    import loguru
    from loguru import logger

    def good_sink(message: loguru.Message):
        print("My name is", message.record["name"])

    def bad_filter(record: loguru.Record):
        return record["invalid"]

    logger.add(good_sink, filter=bad_filter)


.. code-block:: bash

    $ mypy test.py
    test.py:8: error: TypedDict "Record" has no key 'invalid'
    Found 1 error in 1 file (checked 1 source file)

There are several internal types to which you can be exposed using Loguru's public API, they are
listed here and might be useful to type hint your code:

- ``Logger``: the usual |logger| object (also returned by |opt|, |bind| and |patch|).
- ``Message``: the formatted logging message sent to the sinks (a |str| with ``record``
  attribute).
- ``Record``: the |dict| containing all contextual information of the logged message.
- ``Level``: the |namedtuple| returned by |level| (with ``name``, ``no``, ``color`` and ``icon``
  attributes).
- ``Catcher``: the context decorator returned by |catch|.
- ``RecordFile``: the ``record["file"]`` with ``name`` and ``path`` attributes.
- ``RecordLevel``: the ``record["level"]`` with ``name``, ``no`` and ``icon`` attributes.
- ``RecordThread``: the ``record["thread"]`` with ``id`` and ``name`` attributes.
- ``RecordProcess``: the ``record["process"]`` with ``id`` and ``name`` attributes.
- ``RecordException``: the ``record["exception"]`` with ``type``, ``value`` and ``traceback``
  attributes.
"""
import sys
from asyncio import AbstractEventLoop
from datetime import datetime, time, timedelta
from logging import Handler
from types import TracebackType
from typing import (
    Any,
    BinaryIO,
    Callable,
    ContextManager,
    Dict,
    Generator,
    Generic,
    List,
    NamedTuple,
    Optional,
    Pattern,
    Sequence,
    TextIO,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)

if sys.version_info >= (3, 5, 3):
    from typing import Awaitable
else:
    from typing_extensions import Awaitable

if sys.version_info >= (3, 6):
    from os import PathLike
else:
    from pathlib import PurePath as PathLike

if sys.version_info >= (3, 8):
    from typing import TypedDict, Protocol
else:
    from typing_extensions import TypedDict, Protocol

T = TypeVar("T")
Function = Callable[..., T]
ExcInfo = Tuple[Optional[Type[BaseException]], Optional[BaseException], Optional[TracebackType]]

class Level(NamedTuple):
    name: str
    no: int
    color: str
    icon: str

class _RecordAttribute:
    def __repr__(self) -> str: ...
    def __format__(self, spec: str) -> str: ...

class RecordFile(_RecordAttribute):
    name: str
    path: str

class RecordLevel(_RecordAttribute):
    name: str
    no: int
    icon: str

class RecordThread(_RecordAttribute):
    id: int
    name: str

class RecordProcess(_RecordAttribute):
    id: int
    name: str

class RecordException(NamedTuple):
    type: Optional[Type[BaseException]]
    value: Optional[BaseException]
    traceback: Optional[TracebackType]

class Record(TypedDict):
    elapsed: timedelta
    exception: Optional[RecordException]
    extra: dict
    file: RecordFile
    function: str
    level: RecordLevel
    line: int
    message: str
    module: str
    name: Union[str, None]
    process: RecordProcess
    thread: RecordThread
    time: datetime

class Message(str):
    record: Record

class Writable(Protocol):
    def write(self, message: Message) -> None: ...

FilterDict = Dict[Union[str, None], Union[str, int, bool]]
FilterFunction = Callable[[Record], bool]
FormatFunction = Callable[[Record], str]
PatcherFunction = Callable[[Record], None]
RotationFunction = Callable[[Message, TextIO], bool]
RetentionFunction = Callable[[List[str]], None]
CompressionFunction = Callable[[str], None]

class Catcher:
    def __call__(self, function: Function) -> Function: ...
    def __enter__(self) -> None: ...
    def __exit__(
        self,
        type: Optional[Type[BaseException]],
        value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> Optional[bool]: ...

# Actually unusable because TypedDict can't allow extra keys: python/mypy#4617
class _HandlerConfig(TypedDict, total=False):
    sink: Union[str, PathLike, TextIO, Writable, Callable[[Message], None], Handler]
    level: Union[str, int]
    format: Union[str, FormatFunction]
    filter: Optional[Union[str, FilterFunction, FilterDict]]
    colorize: Optional[bool]
    serialize: bool
    backtrace: bool
    diagnose: bool
    enqueue: bool
    catch: bool

class LevelConfig(TypedDict, total=False):
    name: str
    no: int
    color: str
    icon: str

ActivationConfig = Tuple[Union[str, None], bool]

class Logger:
    @overload
    def add(
        self,
        sink: Union[TextIO, Writable, Callable[[Message], None], Handler],
        *,
        level: Union[str, int] = ...,
        format: Union[str, FormatFunction] = ...,
        filter: Optional[Union[str, FilterFunction, FilterDict]] = ...,
        colorize: Optional[bool] = ...,
        serialize: bool = ...,
        backtrace: bool = ...,
        diagnose: bool = ...,
        enqueue: bool = ...,
        catch: bool = ...
    ) -> int: ...
    @overload
    def add(
        self,
        sink: Callable[[Message], Awaitable[None]],
        *,
        level: Union[str, int] = ...,
        format: Union[str, FormatFunction] = ...,
        filter: Optional[Union[str, FilterFunction, FilterDict]] = ...,
        colorize: Optional[bool] = ...,
        serialize: bool = ...,
        backtrace: bool = ...,
        diagnose: bool = ...,
        enqueue: bool = ...,
        catch: bool = ...,
        loop: Optional[AbstractEventLoop] = ...
    ) -> int: ...
    @overload
    def add(
        self,
        sink: Union[str, PathLike],
        *,
        level: Union[str, int] = ...,
        format: Union[str, FormatFunction] = ...,
        filter: Optional[Union[str, FilterFunction, FilterDict]] = ...,
        colorize: Optional[bool] = ...,
        serialize: bool = ...,
        backtrace: bool = ...,
        diagnose: bool = ...,
        enqueue: bool = ...,
        catch: bool = ...,
        rotation: Optional[Union[str, int, time, timedelta, RotationFunction]] = ...,
        retention: Optional[Union[str, int, timedelta, RetentionFunction]] = ...,
        compression: Optional[Union[str, CompressionFunction]] = ...,
        delay: bool = ...,
        mode: str = ...,
        buffering: int = ...,
        encoding: str = ...,
        **kwargs: Any
    ) -> int: ...
    def remove(self, handler_id: Optional[int] = ...) -> None: ...
    async def complete(self) -> None: ...
    @overload
    def catch(
        self,
        exception: Union[Type[BaseException], Tuple[Type[BaseException], ...]] = ...,
        *,
        level: Union[str, int] = ...,
        reraise: bool = ...,
        message: str = ...
    ) -> Catcher: ...
    @overload
    def catch(self, exception: Function = ...) -> Function: ...
    def opt(
        self,
        *,
        exception: Optional[Union[bool, ExcInfo, BaseException]] = ...,
        record: bool = ...,
        lazy: bool = ...,
        colors: bool = ...,
        raw: bool = ...,
        depth: int = ...,
        ansi: bool = ...
    ) -> Logger: ...
    def bind(__self, **kwargs: Any) -> Logger: ...
    def contextualize(__self, **kwargs: Any) -> ContextManager: ...
    def patch(self, patcher: PatcherFunction) -> Logger: ...
    @overload
    def level(self, name: str) -> Level: ...
    @overload
    def level(
        self, name: str, no: int = ..., color: Optional[str] = ..., icon: Optional[str] = ...
    ) -> Level: ...
    @overload
    def level(
        self,
        name: str,
        no: Optional[int] = ...,
        color: Optional[str] = ...,
        icon: Optional[str] = ...,
    ) -> Level: ...
    def disable(self, name: Union[str, None]) -> None: ...
    def enable(self, name: Union[str, None]) -> None: ...
    def configure(
        self,
        *,
        handlers: Sequence[Dict[str, Any]] = ...,
        levels: Optional[Sequence[LevelConfig]] = ...,
        extra: Optional[dict] = ...,
        patcher: Optional[PatcherFunction] = ...,
        activation: Optional[Sequence[ActivationConfig]] = ...
    ) -> List[int]: ...
    # @overload should be used to differentiate bytes and str once python/mypy#7781 is fixed
    @staticmethod
    def parse(
        file: Union[str, PathLike, TextIO, BinaryIO],
        pattern: Union[str, bytes, Pattern[str], Pattern[bytes]],
        *,
        cast: Union[dict, Callable[[dict], None]] = ...,
        chunk: int = ...
    ) -> Generator[dict, None, None]: ...
    @overload
    def trace(__self, __message: str, *args: Any, **kwargs: Any) -> None: ...
    @overload
    def trace(__self, __message: Any) -> None: ...
    @overload
    def debug(__self, __message: str, *args: Any, **kwargs: Any) -> None: ...
    @overload
    def debug(__self, __message: Any) -> None: ...
    @overload
    def info(__self, __message: str, *args: Any, **kwargs: Any) -> None: ...
    @overload
    def info(__self, __message: Any) -> None: ...
    @overload
    def success(__self, __message: str, *args: Any, **kwargs: Any) -> None: ...
    @overload
    def success(__self, __message: Any) -> None: ...
    @overload
    def warning(__self, __message: str, *args: Any, **kwargs: Any) -> None: ...
    @overload
    def warning(__self, __message: Any) -> None: ...
    @overload
    def error(__self, __message: str, *args: Any, **kwargs: Any) -> None: ...
    @overload
    def error(__self, __message: Any) -> None: ...
    @overload
    def critical(__self, __message: str, *args: Any, **kwargs: Any) -> None: ...
    @overload
    def critical(__self, __message: Any) -> None: ...
    @overload
    def exception(__self, __message: str, *args: Any, **kwargs: Any) -> None: ...
    @overload
    def exception(__self, __message: Any) -> None: ...
    @overload
    def log(
        __self, __level: Union[int, str], __message: str, *args: Any, **kwargs: Any
    ) -> None: ...
    @overload
    def log(__self, __level: Union[int, str], __message: Any) -> None: ...
    def start(self, *args: Any, **kwargs: Any): ...
    def stop(self, *args: Any, **kwargs: Any): ...

logger: Logger
