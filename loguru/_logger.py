import functools
import itertools
import logging
import threading
from collections import namedtuple
from datetime import timedelta
from inspect import isclass
from multiprocessing import current_process
from os import PathLike
from os.path import basename, normcase, splitext
from threading import current_thread

from colorama import AnsiToWin32

from . import _defaults
from ._datetime import now
from ._file_sink import FileSink
from ._get_frame import get_frame
from ._handler import Handler
from ._recattrs import ExceptionRecattr, FileRecattr, LevelRecattr, ProcessRecattr, ThreadRecattr

Level = namedtuple("Level", ["no", "color", "icon"])

start_time = now()


class Logger:
    """An object to dispatch logging messages to configured handlers.

    The |Logger| is the core objet of `loguru`, every logging configuration and usage pass through
    a call to one of its methods. There is only one logger, so there is no need to retrieve one
    before usage.

    Handlers to which send log messages are added using the |start| method. Note that you can
    use the |Logger| right after import as it comes pre-configured. Messages can be logged with
    different severity levels and using braces attributes like the |str.format| method do.

    Once a message is logged, a "record" is associated with it. This record is a dict wich contains
    several information about the logging context: time, function, file, line, thread, level...
    It also contains the ``__name__`` of the module, this is why you don't need named loggers.

    You should not instantiate a |Logger| by yourself, use ``from loguru import logger`` instead.

    .. |Logger| replace:: :class:`~Logger`
    .. |start| replace:: :meth:`~Logger.start()`
    .. |stop| replace:: :meth:`~Logger.stop()`
    .. |catch| replace:: :meth:`~Logger.catch()`
    .. |bind| replace:: :meth:`~Logger.bind()`
    .. |opt| replace:: :meth:`~Logger.opt()`
    .. |log| replace:: :meth:`~Logger.log()`
    .. |level| replace:: :meth:`~Logger.level()`
    .. |enable| replace:: :meth:`~Logger.enable()`
    .. |disable| replace:: :meth:`~Logger.disable()`

    .. |str| replace:: :class:`str`
    .. |int| replace:: :class:`int`
    .. |bool| replace:: :class:`bool`
    .. |tuple| replace:: :class:`tuple`
    .. |list| replace:: :class:`list`
    .. |dict| replace:: :class:`dict`
    .. |str.format| replace:: :meth:`str.format()`
    .. |Path| replace:: :class:`pathlib.Path`
    .. |Handler| replace:: :class:`logging.Handler`
    .. |sys.stderr| replace:: :data:`sys.stderr`
    .. |sys.exc_info| replace:: :func:`sys.exc_info()`
    .. |time| replace:: :class:`datetime.time`
    .. |datetime| replace:: :class:`datetime.datetime`
    .. |timedelta| replace:: :class:`datetime.timedelta`
    .. |open| replace:: :func:`open()`
    .. |logging| replace:: :mod:`logging`
    .. |Thread.run| replace:: :meth:`threading.Thread.run()`
    .. |Exception| replace:: :class:`Exception`

    .. |file-like object| replace:: ``file-like object``
    .. _file-like object: https://docs.python.org/3/glossary.html#term-file-object
    .. |class| replace:: ``class``
    .. _class: https://docs.python.org/3/tutorial/classes.html
    .. |function| replace:: ``function``
    .. _function: https://docs.python.org/3/library/functions.html#callable

    .. _Pendulum: https://pendulum.eustace.io/docs/#tokens
    .. _ansimarkup: https://github.com/gvalkov/python-ansimarkup
    .. _better_exceptions: https://github.com/Qix-/better-exceptions
    .. _@sdispater: https://github.com/sdispater
    .. _@gvalkov: https://github.com/gvalkov
    .. _@Qix-: https://github.com/Qix-
    """

    _levels = {
        "TRACE": Level(
            _defaults.LOGURU_TRACE_NO, _defaults.LOGURU_TRACE_COLOR, _defaults.LOGURU_TRACE_ICON
        ),
        "DEBUG": Level(
            _defaults.LOGURU_DEBUG_NO, _defaults.LOGURU_DEBUG_COLOR, _defaults.LOGURU_DEBUG_ICON
        ),
        "INFO": Level(
            _defaults.LOGURU_INFO_NO, _defaults.LOGURU_INFO_COLOR, _defaults.LOGURU_INFO_ICON
        ),
        "SUCCESS": Level(
            _defaults.LOGURU_SUCCESS_NO,
            _defaults.LOGURU_SUCCESS_COLOR,
            _defaults.LOGURU_SUCCESS_ICON,
        ),
        "WARNING": Level(
            _defaults.LOGURU_WARNING_NO,
            _defaults.LOGURU_WARNING_COLOR,
            _defaults.LOGURU_WARNING_ICON,
        ),
        "ERROR": Level(
            _defaults.LOGURU_ERROR_NO, _defaults.LOGURU_ERROR_COLOR, _defaults.LOGURU_ERROR_ICON
        ),
        "CRITICAL": Level(
            _defaults.LOGURU_CRITICAL_NO,
            _defaults.LOGURU_CRITICAL_COLOR,
            _defaults.LOGURU_CRITICAL_ICON,
        ),
    }

    _handlers_count = itertools.count()
    _handlers = {}

    _extra_class = {}

    _min_level = float("inf")
    _enabled = {}
    _activation_list = []

    _lock = threading.Lock()

    def __init__(self, extra, exception, record, lazy, ansi, raw, depth):
        self._extra = extra
        self._record = record
        self._exception = exception
        self._lazy = lazy
        self._ansi = ansi
        self._raw = raw
        self._depth = depth

    def start(
        self,
        sink,
        *,
        level=_defaults.LOGURU_LEVEL,
        format=_defaults.LOGURU_FORMAT,
        filter=_defaults.LOGURU_FILTER,
        colorize=_defaults.LOGURU_COLORIZE,
        serialize=_defaults.LOGURU_SERIALIZE,
        backtrace=_defaults.LOGURU_BACKTRACE,
        enqueue=_defaults.LOGURU_ENQUEUE,
        catch=_defaults.LOGURU_CATCH,
        **kwargs
    ):
        r"""Start sending log messages to a sink adequately configured.

        Parameters
        ----------
        sink : |file-like object|_, |str|, |Path|, |function|_, |Handler| or |class|_
            An object in charge of receiving formatted logging messages and propagating them to an
            appropriate endpoint.
        level : |int| or |str|, optional
            The minimum severity level from which logged messages should be send to the sink.
        format : |str| or |function|_, optional
            The template used to format logged messages before being sent to the sink.
        filter : |function|_ or |str|, optional
            A directive used to optionally filter out logged messages before they are send to the
            sink.
        colorize : |bool|, optional
            Whether or not the color markups contained in the formatted message should be converted
            to ansi codes for terminal coloration, ore stripped otherwise. If ``None``, the choice
            is automatically made based on the sink being a tty or not.
        serialize : |bool|, optional
            Whether or not the logged message and its records should be first converted to a JSON
            string before being sent to the sink.
        backtrace : |bool|, optional
            Whether or not the formatted exception should use stack trace to display local
            variables values. This probably should be set to ``False`` in production to avoid
            leaking sensitive data.
        enqueue : |bool|, optional
            Whether or not the messages to be logged should first pass through a multiprocess-safe
            queue before reaching the sink. This is useful while logging to a file through multiple
            processes.
        catch : |bool|, optional
            Whether or not errors occuring while sink handles logs messages should be caught or not.
            If ``True``, an exception message is displayed on |sys.stderr| but the exception is not
            propagated to the caller, preventing sink from stopping working.
        **kwargs
            Additional parameters that will be passed to the sink while creating it or while
            logging messages (the exact behavior depends on the sink type).


        If and only if the sink is a file, the following parameters apply:

        Parameters
        ----------
        rotation : |str|, |int|, |time|, |timedelta| or |function|_, optional
            A condition indicating whenever the current logged file should be closed and a new one
            started.
        retention : |str|, |int|, |timedelta| or |function|_, optional
            A directive filtering old files that should be removed during rotation or end of
            program.
        compression : |str| or |function|_, optional
            A compression or archive format to which log files should be converted at closure.
        delay : |bool|, optional
            Whether or not the file should be created as soon as the sink is configured, or delayed
            until first logged message. It defaults to ``False``.
        mode : |str|, optional
            The openning mode as for built-in |open| function. It defaults to ``"a"`` (open the
            file in appending mode).
        buffering : |int|, optional
            The buffering policy as for built-in |open| function. It defaults to ``1`` (line
            buffered file).
        encoding : |str|, optional
            The file encoding as for built-in |open| function. If ``None``, it defaults to
            ``locale.getpreferredencoding()``.
        **kwargs
            Others parameters are passed to the built-in |open| function.

        Returns
        -------
        :class:`int`
            An identifier associated with the starteds sink and which should be used to
            |stop| it.

        Notes
        -----
        Extended summary follows.

        .. _sink:

        .. rubric:: The sink parameter

        The ``sink`` handles incomming log messages and proceed to their writing somewhere and
        somehow. A sink can take many forms:

        - A |file-like object|_ like ``sys.stderr`` or ``open("somefile.log", "w")``. Anything with
          a ``.write()`` method is considered as a file-like object. If it has a ``.flush()``
          method, it will be automatically called after each logged message. If it has a ``.stop()``
          method, it will be automatically called at sink termination.
        - A file path as |str| or |Path|. It can be parametrized with some additional parameters,
          see bellow.
        - A simple |function|_ like ``lambda msg: print(msg)``. This allows for logging
          procedure entirely defined by user preferences and needs.
        - A built-in |Handler| like ``logging.StreamHandler``. In such a case, the `Loguru` records
          are automatically converted to the structure expected by the |logging| module.
        - A |class|_ object that will be used to instantiate the sink using ``**kwargs`` attributes
          passed. Hence the class should instantiate objects which are therefore valid sinks.

        .. _message:

        .. rubric:: The logged message

        The logged message passed to all started sinks is nothing more than a string of the
        formatted log, to which a special attribute is associated: the ``.record`` which is a dict
        containing all contextual information possibly needed (see bellow).

        Logged messages are formatted according to the ``format`` of the started sink. This format
        is usually a string containing braces fields to display attributes from the record dict.

        If fine-grained control is needed, the ``format`` can also be a function which takes the
        record as parameter and return the format template string. However, note that in such a
        case, you should take care of appending the line ending and exception field to the returned
        format, while ``"\n{exception}"`` is automatically appended for convenience if ``format`` is
        a string.

        The ``filter`` attribute can be used to control which messages are effectively passed to the
        sink and which one are ignored. A function can be used, accepting the record as an
        argument, and returning ``True`` if the message should be logged, ``False`` otherwise. If
        a string is used, only the records with the same ``name`` and its children will be allowed.

        .. _record:

        .. rubric:: The record dict

        The record is just a Python dict, accessible from sinks by ``message.record``, and usable
        for formatting as ``"{key}"``. Some record's values are objects with two or more attibutes,
        those can be formatted with ``"{key.attr}"`` (``"{key}"`` would display one by default).
        Formatting directives like ``"{key: >3}"`` also works and is specially useful for time (see
        bellow).

        +------------+---------------------------------+----------------------------+
        | Key        | Description                     | Attributes                 |
        +============+=================================+============================+
        | elapsed    | The time elapsed since the      | See |timedelta|            |
        |            | start of the program            |                            |
        +------------+---------------------------------+----------------------------+
        | exception  | The formatted exception if any, | ``type``, ``value``,       |
        |            | ``None`` otherwise              | ``traceback``              |
        +------------+---------------------------------+----------------------------+
        | extra      | The dict of attributes          | None                       |
        |            | bound by the user               |                            |
        +------------+---------------------------------+----------------------------+
        | file       | The file where the logging call | ``name`` (default),        |
        |            | was made                        | ``path``                   |
        +------------+---------------------------------+----------------------------+
        | function   | The function from which the     | None                       |
        |            | logging call was made           |                            |
        +------------+---------------------------------+----------------------------+
        | level      | The severity used to log the    | ``name`` (default),        |
        |            | the message                     | ``no``, ``icon``           |
        +------------+---------------------------------+----------------------------+
        | line       | The line number in the source   | None                       |
        |            | code                            |                            |
        +------------+---------------------------------+----------------------------+
        | message    | The logged message (not yet     | None                       |
        |            | formatted)                      |                            |
        +------------+---------------------------------+----------------------------+
        | module     | The module where the logging    | None                       |
        |            | call was made                   |                            |
        +------------+---------------------------------+----------------------------+
        | name       | The ``__name__`` where the      | None                       |
        |            | logging call was made           |                            |
        +------------+---------------------------------+----------------------------+
        | process    | The process in which the        | ``name``, ``id`` (default) |
        |            | logging call was made           |                            |
        +------------+---------------------------------+----------------------------+
        | thread     | The thread in which the         | ``name``, ``id`` (default) |
        |            | logging call was made           |                            |
        +------------+---------------------------------+----------------------------+
        | time       | The local time when the logging | See |datetime|             |
        |            | call was made                   |                            |
        +------------+---------------------------------+----------------------------+

        .. _time:

        .. rubric:: The time formatting

        The time field can be formatted using more human-friendly tokens. Those constitute a subset
        of the one used by the `Pendulum`_ library by `@sdispater`_. To escape a token, just add
        square brackets around it.

        +------------------------+---------+----------------------------------------+
        |                        | Token   | Output                                 |
        +========================+=========+========================================+
        | Year                   | YYYY    | 2000, 2001, 2002 ... 2012, 2013        |
        |                        +---------+----------------------------------------+
        |                        | YY      | 00, 01, 02 ... 12, 13                  |
        +------------------------+---------+----------------------------------------+
        | Quarter                | Q       | 1 2 3 4                                |
        +------------------------+---------+----------------------------------------+
        | Month                  | MMMM    | January, February, March ...           |
        |                        +---------+----------------------------------------+
        |                        | MMM     | Jan, Feb, Mar ...                      |
        |                        +---------+----------------------------------------+
        |                        | MM      | 01, 02, 03 ... 11, 12                  |
        |                        +---------+----------------------------------------+
        |                        | M       | 1, 2, 3 ... 11, 12                     |
        +------------------------+---------+----------------------------------------+
        | Day of Year            | DDDD    | 001, 002, 003 ... 364, 365             |
        |                        +---------+----------------------------------------+
        |                        | DDD     | 1, 2, 3 ... 364, 365                   |
        +------------------------+---------+----------------------------------------+
        | Day of Month           | DD      | 01, 02, 03 ... 30, 31                  |
        |                        +---------+----------------------------------------+
        |                        | D       | 1, 2, 3 ... 30, 31                     |
        +------------------------+---------+----------------------------------------+
        | Day of Week            | dddd    | Monday, Tuesday, Wednesday ...         |
        |                        +---------+----------------------------------------+
        |                        | ddd     | Mon, Tue, Wed ...                      |
        |                        +---------+----------------------------------------+
        |                        | d       | 0, 1, 2 ... 6                          |
        +------------------------+---------+----------------------------------------+
        | Days of ISO Week       | E       | 1, 2, 3 ... 7                          |
        +------------------------+---------+----------------------------------------+
        | Hour                   | HH      | 00, 01, 02 ... 23, 24                  |
        |                        +---------+----------------------------------------+
        |                        | H       | 0, 1, 2 ... 23, 24                     |
        |                        +---------+----------------------------------------+
        |                        | hh      | 01, 02, 03 ... 11, 12                  |
        |                        +---------+----------------------------------------+
        |                        | h       | 1, 2, 3 ... 11, 12                     |
        +------------------------+---------+----------------------------------------+
        | Minute                 | mm      | 00, 01, 02 ... 58, 59                  |
        |                        +---------+----------------------------------------+
        |                        | m       | 0, 1, 2 ... 58, 59                     |
        +------------------------+---------+----------------------------------------+
        | Second                 | ss      | 00, 01, 02 ... 58, 59                  |
        |                        +---------+----------------------------------------+
        |                        | s       | 0, 1, 2 ... 58, 59                     |
        +------------------------+---------+----------------------------------------+
        | Fractional Second      | S       | 0 1 ... 8 9                            |
        |                        +---------+----------------------------------------+
        |                        | SS      | 00, 01, 02 ... 98, 99                  |
        |                        +---------+----------------------------------------+
        |                        | SSS     | 000 001 ... 998 999                    |
        |                        +---------+----------------------------------------+
        |                        | SSSS... | 000[0..] 001[0..] ... 998[0..] 999[0..]|
        |                        +---------+----------------------------------------+
        |                        | SSSSSS  | 000000 000001 ... 999998 999999        |
        +------------------------+---------+----------------------------------------+
        | AM / PM                | A       | AM, PM                                 |
        +------------------------+---------+----------------------------------------+
        | Timezone               | Z       | -07:00, -06:00 ... +06:00, +07:00      |
        |                        +---------+----------------------------------------+
        |                        | ZZ      | -0700, -0600 ... +0600, +0700          |
        |                        +---------+----------------------------------------+
        |                        | zz      | EST CST ... MST PST                    |
        +------------------------+---------+----------------------------------------+
        | Seconds timestamp      | X       | 1381685817, 1234567890.123             |
        +------------------------+---------+----------------------------------------+
        | Microseconds timestamp | x       | 1234567890123                          |
        +------------------------+---------+----------------------------------------+

        .. _file:

        .. rubric:: The file sinks

        If the sink is a |str| or a |Path|, the corresponding file will be opened for writing logs.
        The path can also contains a special ``"{time}"`` field that will be formatted with the
        current date at file creation.

        The ``rotation`` check is made before logging each messages. If there is already an existing
        file with the same name that the file to be created, then the existing file is renamed by
        appending the date to its basename to prevent file overwritting. This parameter accepts:

        - an |int| which corresponds to the maximum file size in bytes before that the current
          logged file is closed and a new one started over.
        - a |timedelta| which indicates the frequency of each new rotation.
        - a |time| which specifies the hour when the daily rotation should occur.
        - a |str| for human-friendly parametrization of one of the previously enumerated types.
          Examples: ``"100 MB"``, ``"0.5 GB"``, ``"1 month 2 weeks"``, ``"4 days"``, ``"10h"``,
          ``"monthly"``, ``"18:00"``, ``"sunday"``, ``"w0"``, ``"monday at 12:00"``, ...
        - a |function|_ which will be called before logging. It should accept two
          arguments: the logged message and the file object, and it should return ``True`` if
          the rotation should happen now, ``False`` otherwise.

        The ``retention`` occurs at rotation or at sink stop if rotation is ``None``. Files are
        selected according to their basename, if it is the same that the sink file, with possible
        time field being replaced with ``.*``. This parameter accepts:

        - an |int| which indicates the number of log files to keep, while older files are removed.
        - a |timedelta| which specifies the maximum age of files to keep.
        - a |str| for human-friendly parametrization of the maximum age of files to keep.
          Examples: ``"1 week, 3 days"``, ``"2 months"``, ...
        - a |function|_ which will be called before the retention process. It should accept the list
          of log files as argument and process to whatever it wants (moving files, removing them,
          etc.).

        The ``compression`` happens at rotation or at sink stop if rotation is ``None``. This
        parameter acccepts:

        - a |str| which corresponds to the compressed or archived file extension. This can be one
          of: ``"gz"``, ``"bz2"``, ``"xz"``, ``"lzma"``, ``"tar"``, ``"tar.gz"``, ``"tar.bz2"``,
          ``"tar.xz"``, ``"zip"``.
        - a |function|_ which will be called before file termination. It should accept the path
          of the log file as argument and process to whatever it wants (custom compression,
          network sending, removing it, etc.).

        .. _color:

        .. rubric:: The color markups

        To add colors to your logs, you just have to enclose your format string with the appropriate
        tags. This is based on the great `ansimarkup`_ library from `@gvalkov`_. Those tags are
        removed if the sink don't support ansi codes.

        The special tag ``<level>`` (abbreviated with ``<lvl>``) is transformed according to
        the configured color of the logged message level.

        Here are the available tags (note that compatibility may vary depending on terminal):

        +------------------------------------+--------------------------------------+
        | Color (abbr)                       | Styles (abbr)                        |
        +====================================+======================================+
        | Black (k)                          | Bold (b)                             |
        +------------------------------------+--------------------------------------+
        | Blue (e)                           | Dim (d)                              |
        +------------------------------------+--------------------------------------+
        | Cyan (c)                           | Normal (n)                           |
        +------------------------------------+--------------------------------------+
        | Green (g)                          | Italic (i)                           |
        +------------------------------------+--------------------------------------+
        | Magenta (m)                        | Underline (u)                        |
        +------------------------------------+--------------------------------------+
        | Red (r)                            | Strike (s)                           |
        +------------------------------------+--------------------------------------+
        | White (w)                          | Reverse (r)                          |
        +------------------------------------+--------------------------------------+
        | Yellow (y)                         | Blink (l)                            |
        +------------------------------------+--------------------------------------+
        |                                    | Hide (h)                             |
        +------------------------------------+--------------------------------------+

        Usage:

        +-----------------+-------------------------------------------------------------------+
        | Description     | Examples                                                          |
        |                 +---------------------------------+---------------------------------+
        |                 | Foreground                      | Background                      |
        +=================+=================================+=================================+
        | Basic colors    | ``<red>``, ``<r>``              | ``<GREEN>``, ``<G>``            |
        +-----------------+---------------------------------+---------------------------------+
        | Light colors    | ``<light-blue>``, ``<le>``      | ``<LIGHT-CYAN>``, ``<LC>``      |
        +-----------------+---------------------------------+---------------------------------+
        | Xterm colors    | ``<fg 86>``, ``<fg 255>``       | ``<bg 42>``, ``<bg 9>``         |
        +-----------------+---------------------------------+---------------------------------+
        | Hex colors      | ``<fg #00005f>``, ``<fg #EE1>`` | ``<bg #AF5FD7>``, ``<bg #fff>`` |
        +-----------------+---------------------------------+---------------------------------+
        | RGB colors      | ``<fg 0,95,0>``                 | ``<bg 72,119,65>``              |
        +-----------------+---------------------------------+---------------------------------+
        | Stylizing       | ``<bold>``, ``<b>`` , ``<underline>``, ``<u>``                    |
        +-----------------+-------------------------------------------------------------------+
        | Shorthand       | ``<red, yellow>``, ``<r, y>``                                     |
        | (FG, BG)        |                                                                   |
        +-----------------+-------------------------------------------------------------------+
        | Shorthand       | ``<bold, cyan, white>``, ``<b,,w>``, ``<b,c,>``                   |
        | (Style, FG, BG) |                                                                   |
        +-----------------+-------------------------------------------------------------------+

        .. _env:

        .. rubric:: The environment variables

        The default values of sink parameters can be entirely customized. This is particularly
        useful if you don't like the log format of the pre-configured sink.

        Each of the |start| default parameter can be modified by setting the ``LOGURU_[PARAM]``
        environment variable. For example on Linux: ``export LOGURU_FORMAT="{time} - {message}"``
        or ``export LOGURU_ENHANCE=NO``.

        The default levels attributes can also be modified by setting the ``LOGURU_[LEVEL]_[ATTR]``
        environment variable. For example, on Windows: ``setx LOGURU_DEBUG_COLOR="<blue>"``
        or ``setx LOGURU_TRACE_ICON="🚀"``.

        If you want to disable the pre-configured sink, you can set the ``LOGURU_AUTOINIT``
        variable to ``False``.

        Examples
        --------
        >>> logger.start(sys.stdout, format="{time} - {level} - {message}", filter="sub.module")

        >>> logger.start("file_{time}.log", level="TRACE", rotation="100 MB")

        >>> def my_sink(message):
        ...     record = message.record
        ...     update_db(message, time=record.time, level=record.level)
        ...
        >>> logger.start(my_sink)

        >>> from logging import StreamHandler
        >>> logger.start(StreamHandler(sys.stderr), format="{message}")

        >>> class RandomStream:
        ...     def __init__(self, seed, threshold):
        ...         self.threshold = threshold
        ...         random.seed(seed)
        ...     def write(self, message):
        ...         if random.random() > self.threshold:
        ...             print(message)
        ...
        >>> stream_object = RandomStream(seed=12345, threhold=0.25)
        >>> logger.start(stream_object, level="INFO")
        >>> logger.start(RandomStream, level="DEBUG", seed=34567, threshold=0.5)
        """
        if colorize is None and serialize:
            colorize = False

        if isclass(sink):
            sink = sink(**kwargs)
            return self.start(
                sink,
                level=level,
                format=format,
                filter=filter,
                colorize=colorize,
                serialize=serialize,
                backtrace=backtrace,
                enqueue=enqueue,
                catch=catch,
            )
        elif isinstance(sink, (str, PathLike)):
            path = sink
            sink = FileSink(path, **kwargs)
            return self.start(
                sink,
                level=level,
                format=format,
                filter=filter,
                colorize=colorize,
                serialize=serialize,
                backtrace=backtrace,
                enqueue=enqueue,
                catch=catch,
            )
        elif hasattr(sink, "write") and callable(sink.write):
            if colorize is False:
                stream = sink
            else:
                try:
                    converter = AnsiToWin32(sink, convert=None, strip=False)
                    isatty = converter.stream.isatty()
                except Exception:
                    if colorize is None:
                        colorize = False
                    stream = sink
                else:
                    if colorize is None:
                        colorize = isatty
                    if converter.should_wrap() and colorize:
                        stream = converter.stream
                    else:
                        stream = sink

            stream_write = stream.write
            if kwargs:

                def write(m):
                    return stream_write(m, **kwargs)

            else:
                write = stream_write

            if hasattr(stream, "flush") and callable(stream.flush):
                stream_flush = stream.flush

                def writer(m):
                    write(m)
                    stream_flush()

            else:
                writer = write

            if hasattr(stream, "stop") and callable(stream.stop):
                stopper = stream.stop
            else:

                def stopper():
                    return None

        elif isinstance(sink, logging.Handler):

            def writer(m):
                r = m.record
                exc = r["exception"]
                record = logging.root.makeRecord(
                    r["name"],
                    r["level"].no,
                    r["file"].path,
                    r["line"],
                    r["message"],
                    (),
                    (exc.type, exc.value, exc.traceback) if exc else None,
                    r["function"],
                    r["extra"],
                    **kwargs
                )
                sink.handle(record)

            stopper = sink.close
            if colorize is None:
                colorize = False
        elif callable(sink):
            if kwargs:

                def writer(m):
                    return sink(m, **kwargs)

            else:
                writer = sink

            def stopper():
                return None

            if colorize is None:
                colorize = False
        else:
            raise ValueError("Cannot log to objects of type '%s'." % type(sink).__name__)

        if filter is None or filter == "":
            filter_func = None
        elif isinstance(filter, str):
            parent = filter + "."
            length = len(parent)

            def filter_func(r):
                return (r["name"] + ".")[:length] == parent

        elif callable(filter):
            filter_func = filter
        else:
            raise ValueError(
                "Invalid filter, it should be a function or a string, not: '%s'"
                % type(filter).__name__
            )

        if isinstance(level, str):
            levelno = self.level(level).no
        elif isinstance(level, int):
            levelno = level
        else:
            raise ValueError(
                "Invalid level, it should be an integer or a string, not: '%s'"
                % type(level).__name__
            )

        if levelno < 0:
            raise ValueError(
                "Invalid level value, it should be a positive integer, not: %d" % levelno
            )

        if isinstance(format, str):
            formatter = format + "\n{exception}"
            is_formatter_dynamic = False
        elif callable(format):
            formatter = format
            is_formatter_dynamic = True
        else:
            raise ValueError(
                "Invalid format, it should be a string or a function, not: '%s'"
                % type(format).__name__
            )

        try:
            encoding = sink.encoding
        except AttributeError:
            encoding = "ascii"

        with self._lock:
            colors = [lvl.color for lvl in self._levels.values()] + [""]

            handler = Handler(
                writer=writer,
                stopper=stopper,
                levelno=levelno,
                formatter=formatter,
                is_formatter_dynamic=is_formatter_dynamic,
                filter_=filter_func,
                colorize=colorize,
                serialize=serialize,
                backtrace=backtrace,
                catch=catch,
                enqueue=enqueue,
                encoding=encoding,
                colors=colors,
            )

            handler_id = next(self._handlers_count)
            self._handlers[handler_id] = handler
            self.__class__._min_level = min(self.__class__._min_level, levelno)

        return handler_id

    def stop(self, handler_id=None):
        """Stop logging to a previously started sink.

        Parameters
        ----------
        handler_id : |int| or ``None``
            The id of the sink to stop, as it was returned by the |start| method. If ``None``,
            all sinks are stopped. The pre-configured sink is guaranteed to have the index ``0``.

        Examples
        --------
        >>> i = logger.start(sys.stderr, format="{message}")
        >>> logger.info("Logging")
        Logging
        >>> logger.stop(i)
        >>> logger.info("No longer logging")
        """
        with self._lock:
            if handler_id is None:
                for handler in self._handlers.values():
                    handler.stop()
                self._handlers.clear()
            else:
                try:
                    handler = self._handlers.pop(handler_id)
                except KeyError:
                    raise ValueError("There is no started handler with id '%s'" % handler_id)
                handler.stop()

            levelnos = (h.levelno for h in self._handlers.values())
            self.__class__._min_level = min(levelnos, default=float("inf"))

    def catch(
        self,
        exception=Exception,
        *,
        level="ERROR",
        reraise=False,
        message="An error has been caught in function '{record[function]}', "
        "process '{record[process].name}' ({record[process].id}), "
        "thread '{record[thread].name}' ({record[thread].id}):"
    ):
        """Return a decorator to automatically log possibly caught error in wrapped function.

        This is useful to ensure unexpected exceptions are logged, the entire program can be
        wrapped by this method. This is also very useful to decorate |Thread.run| methods while
        using threads to propagate errors to the main logger thread.

        Note that the visibility of variables values (which uses the cool `better_exceptions`_
        library from `@Qix-`_) depends on the ``backtrace`` option of each configured sinks.

        The returned object can also be used as a context manager.

        Parameters
        ----------
        exception : |Exception|, optional
            The type of exception to intercept. If several types should be caught, a tuple of
            exceptions can be used too.
        level : |str| or |int|, optional
            The level name or severity with which the message should be logged.
        reraise : |bool|, optional
            Whether or not the exception should be raised again and hence propagated to the caller.
        message : |str|, optional
            The message that will be automatically logged if an exception occurs. Note that it will
            be formatted with the ``record`` attribute.

        Returns
        -------
        decorator / context manager
            An object that can be used to decorate a function or as a context manager to log
            exceptions possibly caught.

        Examples
        --------
        >>> @logger.catch
        ... def f(x):
        ...     100 / x
        ...
        >>> def g():
        ...     f(10)
        ...     f(0)
        ...
        >>> g()
        ERROR - An error has been caught in function 'g', process 'Main' (367), thread 'ch1' (1398):
        Traceback (most recent call last, catch point marked):
          File "program.py", line 12, in <module>
            g()
            └ <function g at 0x7f225fe2bc80>
        > File "program.py", line 10, in g
            f(0)
            └ <function f at 0x7f225fe2b9d8>
          File "program.py", line 6, in f
            100 / x
                  └ 0
        ZeroDivisionError: division by zero

        >>> with logger.catch(message="Because we never know..."):
        ...    main()  # No exception, no logs
        ...
        """
        if callable(exception) and (
            not isclass(exception) or not issubclass(exception, BaseException)
        ):
            return self.catch()(exception)

        class Catcher:
            def __init__(self, as_decorator):
                self._as_decorator = as_decorator

            def __enter__(self_):
                return None

            def __exit__(self_, type_, value, traceback_):
                if type_ is None:
                    return

                if not issubclass(type_, exception):
                    return False

                if self_._as_decorator:
                    back, decorator = 2, True
                else:
                    back, decorator = 1, False

                logger_ = self.opt(
                    exception=True,
                    record=True,
                    lazy=self._lazy,
                    ansi=self._ansi,
                    raw=self._raw,
                    depth=self._depth + back,
                )

                log = logger_._make_log_function(level, decorator)

                log(logger_, message)

                return not reraise

            def __call__(self_, function):
                catcher = Catcher(True)

                @functools.wraps(function)
                def catch_wrapper(*args, **kwargs):
                    with catcher:
                        return function(*args, **kwargs)

                return catch_wrapper

        return Catcher(False)

    def opt(self, *, exception=None, record=False, lazy=False, ansi=False, raw=False, depth=0):
        r"""Parametrize a logging call to slightly change generated log message.

        Parameters
        ----------
        exception : |bool|, |tuple| or |Exception|, optional
            It if does not evaluate as ``False``, the passed exception is formatted and added to the
            log message. It could be an |Exception| object or a ``(type, value, traceback)`` tuple,
            otherwise the exception information is retrieved from |sys.exc_info|.
        record : |bool|, optional
            If ``True``, the record dict contextualizing the logging call can be used to format the
            message by using ``{record[key]}`` in the log message.
        lazy : |bool|, optional
            If ``True``, the logging call attribute to format the message should be functions which
            will be called only if the level is high enough. This can be used to avoid expensive
            functions if not necessary.
        ansi : |bool|, optional
            If ``True``, logged message will be colorized according to the markups it possibly
            contains.
        raw : |bool|, optional
            If ``True``, the formatting of each sink will be bypassed and the message will be send
            as is.
        depth : |int|, optional
            Specify which stacktrace should be used to contextualize the logged message. This is
            useful while using the logger from inside a wrapped function to retrieve worthwhile
            information.

        Returns
        -------
        :class:`~Logger`
            A logger wrapping the core logger, but transforming logged message adequately before
            sending.

        Examples
        --------
        >>> try:
        ...     1 / 0
        ... except ZeroDivisionError:
        ...    logger.opt(exception=True).debug("Exception logged with debug level:")
        ...
        [18:10:02] DEBUG in '<module>' - Exception logged with debug level:
        Traceback (most recent call last, catch point marked):
        > File "<stdin>", line 2, in <module>
        ZeroDivisionError: division by zero

        >>> logger.opt(record=True).info("Current line is: {record[line]}")
        [18:10:33] INFO in '<module>' - Current line is: 1

        >>> logger.opt(lazy=True).debug("If sink <= DEBUG: {x}", x=lambda: math.factorial(2**5))
        [18:11:19] DEBUG in '<module>' - If sink <= DEBUG: 263130836933693530167218012160000000

        >>> logger.opt(ansi=True).warning("We got a <red>BIG</red> problem")
        [18:11:30] WARNING in '<module>' - We got a BIG problem

        >>> logger.opt(raw=True).debug("No formatting\n")
        No formatting

        >>> def wrapped():
        ...     logger.opt(depth=1).info("Get parent context")
        ...
        >>> def func():
        ...     wrapped()
        ...
        >>> func()
        [18:11:54] DEBUG in 'func' - Get parent context
        """
        return Logger(self._extra, exception, record, lazy, ansi, raw, depth)

    def bind(_self, **kwargs):
        """Bind attributes to the ``extra`` dict of each logged message record.

        This is used to add custom context to each logging call.

        Parameters
        ----------
        **kwargs
            Mapping between keys and values that will be added to the ``extra`` dict.

        Returns
        -------
        :class:`~Logger`
            A logger wrapping the core logger, but which sends record with the customized ``extra``
            dict.

        Examples
        --------
        >>> logger.start(sys.stderr, format="{extra[ip]} - {message}")
        1
        >>> class Server:
        ...     def __init__(self, ip):
        ...         self.ip = ip
        ...         self.logger = logger.bind(ip=ip)
        ...     def call(self, message):
        ...         self.logger.info(message)
        ...
        >>> instance_1 = Server("192.168.0.200")
        >>> instance_2 = Server("127.0.0.1")
        >>> instance_1.call("First instance")
        192.168.0.200 - First instance
        >>> instance_2.call("Second instance")
        127.0.0.1 - Second instance
        """
        return Logger(
            {**_self._extra, **kwargs},
            _self._exception,
            _self._record,
            _self._lazy,
            _self._ansi,
            _self._raw,
            _self._depth,
        )

    def level(self, name, no=None, color=None, icon=None):
        """Add, update or retrieve a logging level.

        Logging levels are defined by their ``name`` to which a severity ``no``, an ansi ``color``
        and an ``icon`` are associated and possibly modified at run-time. To |log| to a custom
        level, you should necessarily use its name, the severity number is not linked back to levels
        name (this implies that several levels can share the same severity).

        To add a new level, all parameters should be passed so it can be properly configured.

        To update an existing level, pass its ``name`` with the parameters to be changed.

        To retrieve level information, the ``name`` solely suffices.

        Parameters
        ----------
        name : |str|
            The name of the logging level.
        no : |int|
            The severity of the level to be added or updated.
        color : |str|
            The color markup of the level to be added or updated.
        icon : |str|
            The icon of the level to be added or updated.

        Returns
        -------
        ``Level``
            A namedtuple containing information about the level.

        Examples
        --------
        >>> level = logger.level("ERROR")
        Level(no=40, color='<red><bold>', icon='❌')
        >>> logger.start(sys.stderr, format="{level.no} {icon} {message}")
        >>> logger.level("CUSTOM", no=15, color="<blue>", icon="@")
        >>> logger.log("CUSTOM", "Logging...")
        15 @ Logging...
        >>> logger.level("WARNING", icon=r"/!\\")
        >>> logger.warning("Updated!")
        30 /!\\ Updated!
        """
        if not isinstance(name, str):
            raise ValueError(
                "Invalid level name, it should be a string, not: '%s'" % type(name).__name__
            )

        if no is color is icon is None:
            try:
                return self._levels[name]
            except KeyError:
                raise ValueError("Level '%s' does not exist" % name)

        if name not in self._levels:
            if no is None:
                raise ValueError(
                    "Level '%s' does not exist, you have to create it by specifying a level no"
                    % name
                )
            else:
                old_no, old_color, old_icon = None, "", " "
        else:
            old_no, old_color, old_icon = self.level(name)

        if no is None:
            no = old_no

        if color is None:
            color = old_color

        if icon is None:
            icon = old_icon

        if not isinstance(no, int):
            raise ValueError(
                "Invalid level no, it should be an integer, not: '%s'" % type(no).__name__
            )

        if no < 0:
            raise ValueError("Invalid level no, it should be a positive integer, not: %d" % no)

        self._levels[name] = Level(no, color, icon)

        with self._lock:
            for handler in self._handlers.values():
                handler.update_format(color)

        return self.level(name)

    def disable(self, name):
        """Disable logging of messages comming from ``name`` module and its children.

        Developers of library using `Loguru` should absolutely disable it to avoid disrupting
        users with unrelated logs messages.

        Parameters
        ----------
        name : |str|
            The name of the parent module to disable.

        Examples
        --------
        >>> logger.info("Allowed message by default")
        [22:21:55] Allowed message by default
        >>> logger.disable("my_library")
        >>> logger.info("While publishing a library, don't forget to disable logging")
        """
        self._change_activation(name, False)

    def enable(self, name):
        """Enable logging of messages comming from ``name`` module and its children.

        Logging is generally disabled by imported library using `Loguru`, hence this function
        allows users to receive these messages anyway.

        Parameters
        ----------
        name : |str|
            The name of the parent module to re-allow.

        Examples
        --------
        >>> logger.disable("__main__")
        >>> logger.info("Disabled, so nothing is logged.")
        >>> logger.enable("__main__")
        >>> logger.info("Re-enabled, messages are logged.")
        [22:46:12] Re-enabled, messages are logged.
        """
        self._change_activation(name, True)

    def configure(self, *, handlers=None, levels=None, extra=None, activation=None):
        """Configure the core logger.

        Parameters
        ----------
        handlers : |list| of |dict|, optional
            A list of each handler to be started. The list should contains dicts of params passed to
            the |start| function as keyword arguments. If not ``None``, all previously started
            handlers are first stopped.
        levels : |list| of |dict|, optional
            A list of each level to be added or updated. The list should contains dicts of params
            passed to the |level| function as keyword arguments. This will never remove previously
            created levels.
        extra : |dict|, optional
            A dict containing additional parameters bound to the core logger, useful to share
            common properties if you call |bind| in several of your files modules. If not ``None``,
            this will remove previously configured ``extra`` dict.
        activation : |list| of |tuple|, optional
            A list of ``(name, state)`` tuples which denotes which loggers should be enabled (if
            `state` is ``True``) or disabled (if `state` is ``False``). The calls to |enable|
            and |disable| are made accordingly to the list order. This will not modify previously
            activated loggers, so if you need a fresh start preprend your list with ``("", False)``
            or ``("", True)``.

        Returns
        -------
        :class:`list` of :class:`int`
            A list containing the identifiers of possibly started sinks.

        Examples
        --------
        >>> logger.configure(
        ...     handlers=[dict(sink=sys.stderr, format="[{time}] {message}"),
        ...            dict(sink="file.log", enqueue=True, serialize=True)],
        ...     levels=[dict(name="NEW", no=13, icon="¤", color="")],
        ...     extra={"common_to_all": "default"},
        ...     activation=[("my_module.secret": False, "another_library.module": True)]
        ... )
        [1, 2]
        """
        if handlers is not None:
            self.stop()
        else:
            handlers = []

        if levels is not None:
            for params in levels:
                self.level(**params)

        if extra is not None:
            with self._lock:
                self._extra_class.clear()
                self._extra_class.update(extra)

        if activation is not None:
            for name, state in activation:
                if state:
                    self.enable(name)
                else:
                    self.disable(name)

        return [self.start(**params) for params in handlers]

    def _change_activation(self, name, status):
        if not isinstance(name, str):
            raise ValueError("Invalid name, it should be a string, not: '%s'" % type(name).__name__)

        if name != "":
            name += "."

        with self._lock:
            activation_list = [(n, s) for n, s in self._activation_list if n[: len(name)] != name]

        parent_status = next((s for n, s in activation_list if name[: len(n)] == n), None)
        if parent_status != status and not (name == "" and status == True):
            activation_list.append((name, status))

            def key_sort(x):
                return x[0].count(".")

            activation_list.sort(key=key_sort, reverse=True)

        with self._lock:
            for n in self._enabled:
                if (n + ".")[: len(name)] == name:
                    self._enabled[n] = status

            self._activation_list[:] = activation_list

    @staticmethod
    @functools.lru_cache()
    def _make_log_function(level, decorated=False):

        if isinstance(level, str):
            level_id = level_name = level
        elif isinstance(level, int):
            if level < 0:
                raise ValueError(
                    "Invalid level value, it should be a positive integer, not: %d" % level
                )
            level_id = None
            level_name = "Level %d" % level
        else:
            raise ValueError(
                "Invalid level, it should be an integer or a string, not: '%s'"
                % type(level).__name__
            )

        def log_function(_self, _message, *args, **kwargs):
            if not _self._handlers:
                return

            frame = get_frame(_self._depth + 1)
            name = frame.f_globals["__name__"]

            try:
                if not _self._enabled[name]:
                    return
            except KeyError:
                dotted_name = name + "."
                for dotted_module_name, status in _self._activation_list:
                    if dotted_name[: len(dotted_module_name)] == dotted_module_name:
                        if status:
                            break
                        _self._enabled[name] = False
                        return
                _self._enabled[name] = True

            current_datetime = now()

            if level_id is None:
                level_no, level_color, level_icon = level, "", " "
            else:
                try:
                    level_no, level_color, level_icon = _self._levels[level_name]
                except KeyError:
                    raise ValueError("Level '%s' does not exist" % level_name)

            if level_no < _self._min_level:
                return

            code = frame.f_code
            file_path = normcase(code.co_filename)
            file_name = basename(file_path)
            thread = current_thread()
            process = current_process()
            elapsed = current_datetime - start_time

            level_recattr = LevelRecattr(level_name)
            level_recattr.no, level_recattr.name, level_recattr.icon = (
                level_no,
                level_name,
                level_icon,
            )

            file_recattr = FileRecattr(file_name)
            file_recattr.name, file_recattr.path = file_name, file_path

            thread_ident = thread.ident
            thread_recattr = ThreadRecattr(thread_ident)
            thread_recattr.id, thread_recattr.name = thread_ident, thread.name

            process_ident = process.ident
            process_recattr = ProcessRecattr(process_ident)
            process_recattr.id, process_recattr.name = process_ident, process.name

            if _self._exception:
                exception = ExceptionRecattr(_self._exception, decorated)
            else:
                exception = None

            record = {
                "elapsed": elapsed,
                "exception": exception,
                "extra": {**_self._extra_class, **_self._extra},
                "file": file_recattr,
                "function": code.co_name,
                "level": level_recattr,
                "line": frame.f_lineno,
                "message": _message,
                "module": splitext(file_name)[0],
                "name": name,
                "process": process_recattr,
                "thread": thread_recattr,
                "time": current_datetime,
            }

            if _self._lazy:
                args = [arg() for arg in args]
                kwargs = {key: value() for key, value in kwargs.items()}

            if _self._record:
                record["message"] = _message.format(*args, **kwargs, record=record)
            elif args or kwargs:
                record["message"] = _message.format(*args, **kwargs)

            for handler in _self._handlers.values():
                handler.emit(record, level_color, _self._ansi, _self._raw)

        doc = r"Log ``_message.format(*args, **kwargs)`` with severity ``'%s'``." % level_name
        log_function.__doc__ = doc

        return log_function

    trace = _make_log_function.__func__("TRACE")
    debug = _make_log_function.__func__("DEBUG")
    info = _make_log_function.__func__("INFO")
    success = _make_log_function.__func__("SUCCESS")
    warning = _make_log_function.__func__("WARNING")
    error = _make_log_function.__func__("ERROR")
    critical = _make_log_function.__func__("CRITICAL")

    def log(_self, _level, _message, *args, **kwargs):
        r"""Log ``_message.format(*args, **kwargs)`` with severity ``_level``."""
        logger = _self.opt(
            exception=_self._exception,
            record=_self._record,
            lazy=_self._lazy,
            ansi=_self._ansi,
            raw=_self._raw,
            depth=_self._depth + 1,
        )
        logger._make_log_function(_level)(logger, _message, *args, **kwargs)

    def exception(_self, _message, *args, **kwargs):
        r"""Convenience method for logging an ``'ERROR'`` with exception information."""
        logger = _self.opt(
            exception=True,
            record=_self._record,
            lazy=_self._lazy,
            ansi=_self._ansi,
            raw=_self._raw,
            depth=_self._depth + 1,
        )
        logger._make_log_function("ERROR")(logger, _message, *args, **kwargs)
