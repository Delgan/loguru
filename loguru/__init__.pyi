import sys
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
    name: str
    process: RecordProcess
    thread: RecordThread
    time: datetime

class Message(str):
    record: Record

class Writable(Protocol):
    def write(self, message: Message) -> None: ...

FilterFunction = Callable[[Record], bool]
FormatFunction = Callable[[Record], str]
PatcherFunction = Callable[[Record], None]
RotationFunction = Callable[[Message, TextIO], bool]
RetentionFunction = Callable[[List[str]], None]
CompressionFunction = Callable[[str], None]

class ContextDecorator:
    def __call__(self, function: Function) -> Function: ...
    def __enter__(self) -> None: ...
    def __exit__(
        self,
        type: Optional[Type[BaseException]],
        value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> Optional[bool]: ...

# Actually unusable because TypedDict can't allow extra keys: mypy/4617
class _HandlerConfig(TypedDict, total=False):
    sink: Union[str, PathLike, TextIO, Writable, Callable[[Message], None], Handler]
    level: Union[str, int]
    format: Union[str, FormatFunction]
    filter: Union[str, FilterFunction]
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
        filter: Union[str, FilterFunction] = ...,
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
        sink: Union[str, PathLike],
        *,
        level: Union[str, int] = ...,
        format: Union[str, FormatFunction] = ...,
        filter: Union[str, FilterFunction] = ...,
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
    @overload
    def catch(
        self,
        exception: Union[Type[BaseException], Tuple[Type[BaseException], ...]] = ...,
        *,
        level: Union[str, int] = ...,
        reraise: bool = ...,
        message: str = ...
    ) -> ContextDecorator: ...
    @overload
    def catch(self, exception: Function = ...) -> Function: ...
    def opt(
        self,
        *,
        exception: Optional[Union[bool, ExcInfo, BaseException]] = ...,
        record: bool = ...,
        lazy: bool = ...,
        ansi: bool = ...,
        raw: bool = ...,
        depth: int = ...
    ) -> Logger: ...
    def bind(__self, **kwargs: Any) -> Logger: ...
    def contextualize(__self, **kwargs: Any) -> ContextManager: ...
    def patch(self, patcher: PatcherFunction) -> Logger: ...
    @overload
    def level(self, name: str) -> Level: ...
    @overload
    def level(self, name: str, no: int = ..., color: str = ..., icon: str = ...) -> Level: ...
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
    ): ...
    # @overload should be used to differentiate bytes and str once mypy/7781 is fixed
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
