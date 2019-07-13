import functools
import inspect
import itertools
import logging
import re
import sys
import threading
import warnings
from collections import namedtuple
from inspect import isclass
from multiprocessing import current_process
from os.path import basename, splitext
from threading import current_thread

from . import _colorama
from . import _defaults
from ._ansimarkup import AnsiMarkup
from ._better_exceptions import ExceptionFormatter
from ._datetime import aware_now
from ._file_sink import FileSink
from ._get_frame import get_frame
from ._handler import Handler
from ._recattrs import ExceptionRecattr, FileRecattr, LevelRecattr, ProcessRecattr, ThreadRecattr

try:
    from os import PathLike
except ImportError:
    from pathlib import PurePath as PathLike


def parse_ansi(color):
    return AnsiMarkup(strip=False).feed(color.strip(), strict=False)


Level = namedtuple("Level", ["no", "color", "icon"])

start_time = aware_now()


class Logger:
    """An object to dispatch logging messages to configured handlers.

    The |Logger| is the core object of `loguru`, every logging configuration and usage pass through
    a call to one of its methods. There is only one logger, so there is no need to retrieve one
    before usage.

    Once the ``logger`` is imported, it can be used to write messages about events happening in your
    code. By reading the output logs of your application, you gain a better understanding of the
    flow of your program and you more easily track and debug unexpected behaviors.

    Handlers to which the logger sends log messages are added using the |add| method. Note that you
    can use the |Logger| right after import as it comes pre-configured (logs are emitted to
    |sys.stderr| by default). Messages can be logged with different severity levels and using braces
    attributes like the |str.format| method do.

    When a message is logged, a "record" is associated with it. This record is a dict which contains
    information about the logging context: time, function, file, line, thread, level... It also
    contains the ``__name__`` of the module, this is why you don't need named loggers.

    You should not instantiate a |Logger| by yourself, use ``from loguru import logger`` instead.

    .. |Logger| replace:: :class:`~Logger`
    .. |add| replace:: :meth:`~Logger.add()`
    .. |remove| replace:: :meth:`~Logger.remove()`
    .. |catch| replace:: :meth:`~Logger.catch()`
    .. |bind| replace:: :meth:`~Logger.bind()`
    .. |patch| replace:: :meth:`~Logger.patch()`
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
    .. |match.groupdict| replace:: :meth:`re.Match.groupdict()`
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
    .. |locale.getpreferredencoding| replace:: :func:`locale.getpreferredencoding()`

    .. |logger.trace| replace:: :meth:`logger.trace()<Logger.trace()>`
    .. |logger.debug| replace:: :meth:`logger.debug()<Logger.debug()>`
    .. |logger.info| replace:: :meth:`logger.info()<Logger.info()>`
    .. |logger.success| replace:: :meth:`logger.success()<Logger.success()>`
    .. |logger.warning| replace:: :meth:`logger.warning()<Logger.warning()>`
    .. |logger.error| replace:: :meth:`logger.error()<Logger.error()>`
    .. |logger.critical| replace:: :meth:`logger.critical()<Logger.critical()>`

    .. |file-like object| replace:: ``file-like object``
    .. _file-like object: https://docs.python.org/3/glossary.html#term-file-object
    .. |class| replace:: ``class``
    .. _class: https://docs.python.org/3/tutorial/classes.html
    .. |function| replace:: ``function``
    .. _function: https://docs.python.org/3/library/functions.html#callable
    .. |re.Pattern| replace:: ``re.Pattern``
    .. _re.Pattern: https://docs.python.org/3/library/re.html#re-objects
    .. |re.Match| replace:: ``re.Match``
    .. _re.Match: https://docs.python.org/3/library/re.html#match-objects

    .. _Pendulum: https://pendulum.eustace.io/docs/#tokens
    .. _better_exceptions: https://github.com/Qix-/better-exceptions
    .. _@sdispater: https://github.com/sdispater
    .. _@Qix-: https://github.com/Qix-
    .. _Formatting directives: https://docs.python.org/3/library/string.html#format-string-syntax
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
    _levels_ansi_codes = {name: parse_ansi(level.color) for name, level in _levels.items()}
    _levels_ansi_codes[None] = ""

    _handlers_count = itertools.count()
    _handlers = {}

    _extra_class = {}
    _patcher_class = None

    _min_level = float("inf")
    _enabled = {}
    _activation_list = []
    _activation_none = True

    _lock = threading.Lock()

    def __init__(self, exception, depth, record, lazy, ansi, raw, patcher, extra):
        self._options = (exception, depth, record, lazy, ansi, raw, patcher, extra)

    def add(
        self,
        sink,
        *,
        level=_defaults.LOGURU_LEVEL,
        format=_defaults.LOGURU_FORMAT,
        filter=_defaults.LOGURU_FILTER,
        colorize=_defaults.LOGURU_COLORIZE,
        serialize=_defaults.LOGURU_SERIALIZE,
        backtrace=_defaults.LOGURU_BACKTRACE,
        diagnose=_defaults.LOGURU_DIAGNOSE,
        enqueue=_defaults.LOGURU_ENQUEUE,
        catch=_defaults.LOGURU_CATCH,
        **kwargs
    ):
        r"""Add a handler sending log messages to a sink adequately configured.

        Parameters
        ----------
        sink : |file-like object|_, |str|, |Path|, |function|_, |Handler| or |class|_
            An object in charge of receiving formatted logging messages and propagating them to an
            appropriate endpoint.
        level : |int| or |str|, optional
            The minimum severity level from which logged messages should be sent to the sink.
        format : |str| or |function|_, optional
            The template used to format logged messages before being sent to the sink.
        filter : |function|_ or |str|, optional
            A directive optionally used to decide for each logged message whether it should be sent
            to the sink or not.
        colorize : |bool|, optional
            Whether the color markups contained in the formatted message should be converted to ansi
            codes for terminal coloration, or stripped otherwise. If ``None``, the choice is
            automatically made based on the sink being a tty or not.
        serialize : |bool|, optional
            Whether the logged message and its records should be first converted to a JSON string
            before being sent to the sink.
        backtrace : |bool|, optional
            Whether the exception trace formatted should be extended upward, beyond the catching
            point, to show the full stacktrace which generated the error.
        diagnose : |bool|, optional
            Whether the exception trace should display the variables values to eases the debugging.
            This should be set to ``False`` in production to avoid leaking sensitive data.
        enqueue : |bool|, optional
            Whether the messages to be logged should first pass through a multiprocess-safe queue
            before reaching the sink. This is useful while logging to a file through multiple
            processes.
        catch : |bool|, optional
            Whether errors occurring while sink handles logs messages should be automatically
            caught. If ``True``, an exception message is displayed on |sys.stderr| but the exception
            is not propagated to the caller, preventing your app to crash.
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
            Whether the file should be created as soon as the sink is configured, or delayed until
            first logged message. It defaults to ``False``.
        mode : |str|, optional
            The opening mode as for built-in |open| function. It defaults to ``"a"`` (open the
            file in appending mode).
        buffering : |int|, optional
            The buffering policy as for built-in |open| function. It defaults to ``1`` (line
            buffered file).
        encoding : |str|, optional
            The file encoding as for built-in |open| function. If ``None``, it defaults to
            |locale.getpreferredencoding|.
        **kwargs
            Others parameters are passed to the built-in |open| function.

        Returns
        -------
        :class:`int`
            An identifier associated with the added sink and which should be used to
            |remove| it.

        Notes
        -----
        Extended summary follows.

        .. _sink:

        .. rubric:: The sink parameter

        The ``sink`` handles incoming log messages and proceed to their writing somewhere and
        somehow. A sink can take many forms:

        - A |file-like object|_ like ``sys.stderr`` or ``open("somefile.log", "w")``. Anything with
          a ``.write()`` method is considered as a file-like object. If it has a ``.flush()``
          method, it will be automatically called after each logged message. If it has a ``.stop()``
          method, it will be automatically called at sink termination.
        - A file path as |str| or |Path|. It can be parametrized with some additional parameters,
          see below.
        - A simple |function|_ like ``lambda msg: print(msg)``. This allows for logging
          procedure entirely defined by user preferences and needs.
        - A built-in |Handler| like ``logging.StreamHandler``. In such a case, the `Loguru` records
          are automatically converted to the structure expected by the |logging| module.
        - A |class|_ object that will be used to instantiate the sink using ``**kwargs`` attributes
          passed. Hence, the class should instantiate objects which are therefore valid sinks.

        Note that you should avoid using  the ``logger`` inside any of your sinks as this would
        result in infinite recursion or dead lock if the module's sink was not explicitly disabled.

        .. _message:

        .. rubric:: The logged message

        The logged message passed to all added sinks is nothing more than a string of the
        formatted log, to which a special attribute is associated: the ``.record`` which is a dict
        containing all contextual information possibly needed (see below).

        Logged messages are formatted according to the ``format`` of the added sink. This format
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

        .. _levels:

        .. rubric:: The severity levels

        Each logged message is associated with a severity level. These levels make it possible to
        prioritize messages and to choose the verbosity of the logs according to usages. For
        example, it allows to display some debugging information to a developer, while hiding it to
        the end user running the application.

        The ``level`` attribute of every added sink controls the minimum threshold from which log
        messages are allowed to be emitted. While using the ``logger``, you are in charge of
        configuring the appropriate granularity of your logs. It is possible to add even more custom
        levels by using the |level| method.

        Here are the standard levels with their default severity value, each one is associated with
        a logging method of the same name:

        +----------------------+------------------------+------------------------+
        | Level name           | Severity value         | Logger method          |
        +======================+========================+========================+
        | ``TRACE``            | 5                      | |logger.trace|         |
        +----------------------+------------------------+------------------------+
        | ``DEBUG``            | 10                     | |logger.debug|         |
        +----------------------+------------------------+------------------------+
        | ``INFO``             | 20                     | |logger.info|          |
        +----------------------+------------------------+------------------------+
        | ``SUCCESS``          | 25                     | |logger.success|       |
        +----------------------+------------------------+------------------------+
        | ``WARNING``          | 30                     | |logger.warning|       |
        +----------------------+------------------------+------------------------+
        | ``ERROR``            | 40                     | |logger.error|         |
        +----------------------+------------------------+------------------------+
        | ``CRITICAL``         | 50                     | |logger.critical|      |
        +----------------------+------------------------+------------------------+

        .. _record:

        .. rubric:: The record dict

        The record is just a Python dict, accessible from sinks by ``message.record``. It contains
        all contextual information of the logging call (time, function, file, line, level, etc.).

        Each of its key can be used in the handler's ``format`` so the corresponding value is
        properly displayed in the logged message (e.g. ``"{level}"`` -> ``"INFO"``). Some record's
        values are objects with two or more attributes, these can be formatted with ``"{key.attr}"``
        (``"{key}"`` would display one by default). `Formatting directives`_ like ``"{key: >3}"``
        also works and is particularly useful for time (see below).

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
        |            | bound by the user (see |bind|)  |                            |
        +------------+---------------------------------+----------------------------+
        | file       | The file where the logging call | ``name`` (default),        |
        |            | was made                        | ``path``                   |
        +------------+---------------------------------+----------------------------+
        | function   | The function from which the     | None                       |
        |            | logging call was made           |                            |
        +------------+---------------------------------+----------------------------+
        | level      | The severity used to log the    | ``name`` (default),        |
        |            | message                         | ``no``, ``icon``           |
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
        | time       | The aware local time when the   | See |datetime|             |
        |            | logging call was made           |                            |
        +------------+---------------------------------+----------------------------+

        .. _time:

        .. rubric:: The time formatting

        To use your favorite time representation, you can set it directly in the time formatter
        specifier of your handler format, like for example ``format="{time:HH:mm:ss} {message}"``.
        Note that this datetime represents your local time, and it is also made timezone-aware,
        so you can display the UTC offset to avoid ambiguities.

        The time field can be formatted using more human-friendly tokens. These constitute a subset
        of the one used by the `Pendulum`_ library of `@sdispater`_. To escape a token, just add
        square brackets around it, for example ``"[YY]"`` would display literally ``"YY"``.

        If no time formatter specifier is used, like for example if ``format="{time} {message}"``,
        the default one will use ISO 8601.

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
        The path can also contain a special ``"{time}"`` field that will be formatted with the
        current date at file creation.

        The ``rotation`` check is made before logging each message. If there is already an existing
        file with the same name that the file to be created, then the existing file is renamed by
        appending the date to its basename to prevent file overwriting. This parameter accepts:

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
        parameter accepts:

        - a |str| which corresponds to the compressed or archived file extension. This can be one
          of: ``"gz"``, ``"bz2"``, ``"xz"``, ``"lzma"``, ``"tar"``, ``"tar.gz"``, ``"tar.bz2"``,
          ``"tar.xz"``, ``"zip"``.
        - a |function|_ which will be called before file termination. It should accept the path
          of the log file as argument and process to whatever it wants (custom compression,
          network sending, removing it, etc.).

        .. _color:

        .. rubric:: The color markups

        To add colors to your logs, you just have to enclose your format string with the appropriate
        tags (e.g. ``<tag>some message</tag>``). These tags are automatically removed if the sink
        doesn't support ansi codes. For convenience, you can use ``</>`` to close the last opening
        tag without repeating its name (e.g. ``<tag>another message</>``).

        The special tag ``<level>`` (abbreviated with ``<lvl>``) is transformed according to
        the configured color of the logged message level.

        Tags which are not recognized will raise an exception during parsing, to inform you about
        possible misuse. If you wish to display a markup tag literally, you can escape it by
        prepending a ``\`` like for example ``\<blue>``. If, for some reason, you need to escape a
        string programmatically, note that the regex used internally to parse markup tags is
        ``r"\\?</?((?:[fb]g\s)?[^<>\s]*)>"``.

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
        | 8-bit colors    | ``<fg 86>``, ``<fg 255>``       | ``<bg 42>``, ``<bg 9>``         |
        +-----------------+---------------------------------+---------------------------------+
        | Hex colors      | ``<fg #00005f>``, ``<fg #EE1>`` | ``<bg #AF5FD7>``, ``<bg #fff>`` |
        +-----------------+---------------------------------+---------------------------------+
        | RGB colors      | ``<fg 0,95,0>``                 | ``<bg 72,119,65>``              |
        +-----------------+---------------------------------+---------------------------------+
        | Stylizing       | ``<bold>``, ``<b>``,  ``<underline>``, ``<u>``                    |
        +-----------------+-------------------------------------------------------------------+

        .. _env:

        .. rubric:: The environment variables

        The default values of sink parameters can be entirely customized. This is particularly
        useful if you don't like the log format of the pre-configured sink.

        Each of the |add| default parameter can be modified by setting the ``LOGURU_[PARAM]``
        environment variable. For example on Linux: ``export LOGURU_FORMAT="{time} - {message}"``
        or ``export LOGURU_DIAGNOSE=NO``.

        The default levels' attributes can also be modified by setting the ``LOGURU_[LEVEL]_[ATTR]``
        environment variable. For example, on Windows: ``setx LOGURU_DEBUG_COLOR "<blue>"``
        or ``setx LOGURU_TRACE_ICON "🚀"``.

        If you want to disable the pre-configured sink, you can set the ``LOGURU_AUTOINIT``
        variable to ``False``.

        On Linux, you will probably need to edit the ``~/.profile`` file to make this persistent. On
        Windows, don't forget to restart your terminal for the change to be taken into account.

        Examples
        --------
        >>> logger.add(sys.stdout, format="{time} - {level} - {message}", filter="sub.module")

        >>> logger.add("file_{time}.log", level="TRACE", rotation="100 MB")

        >>> def my_sink(message):
        ...     record = message.record
        ...     update_db(message, time=record.time, level=record.level)
        ...
        >>> logger.add(my_sink)

        >>> from logging import StreamHandler
        >>> logger.add(StreamHandler(sys.stderr), format="{message}")

        >>> class RandomStream:
        ...     def __init__(self, seed, threshold):
        ...         self.threshold = threshold
        ...         random.seed(seed)
        ...     def write(self, message):
        ...         if random.random() > self.threshold:
        ...             print(message)
        ...
        >>> stream_object = RandomStream(seed=12345, threhold=0.25)
        >>> logger.add(stream_object, level="INFO")
        >>> logger.add(RandomStream, level="DEBUG", seed=34567, threshold=0.5)
        """
        if colorize is None and serialize:
            colorize = False

        if isclass(sink):
            sink = sink(**kwargs)
            return self.add(
                sink,
                level=level,
                format=format,
                filter=filter,
                colorize=colorize,
                serialize=serialize,
                backtrace=backtrace,
                diagnose=diagnose,
                enqueue=enqueue,
                catch=catch,
            )
        elif isinstance(sink, (str, PathLike)):
            path = sink
            sink = FileSink(path, **kwargs)
            return self.add(
                sink,
                level=level,
                format=format,
                filter=filter,
                colorize=colorize,
                serialize=serialize,
                backtrace=backtrace,
                diagnose=diagnose,
                enqueue=enqueue,
                catch=catch,
            )
        elif hasattr(sink, "write") and callable(sink.write):
            name = getattr(sink, "name", repr(sink))

            if colorize is None:
                colorize = _colorama.should_colorize(sink)

            if colorize is True and _colorama.should_wrap(sink):
                stream = _colorama.wrap(sink)
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
            name = repr(sink)

            def writer(m):
                message = str(m)
                r = m.record
                exc = r["exception"]
                if not is_formatter_dynamic:
                    message = message[:-1]
                record = logging.root.makeRecord(
                    r["name"],
                    r["level"].no,
                    r["file"].path,
                    r["line"],
                    message,
                    (),
                    (exc.type, exc.value, exc.traceback) if exc else None,
                    r["function"],
                    r["extra"],
                    **kwargs
                )
                if exc:
                    record.exc_text = "\n"
                sink.handle(record)

            stopper = sink.close
            if colorize is None:
                colorize = False
        elif callable(sink):
            name = getattr(sink, "__name__", repr(sink))

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

        if filter is None:
            filter_func = None
        elif filter == "":

            def filter_func(record):
                return record["name"] is not None

        elif isinstance(filter, str):
            parent = filter + "."
            length = len(parent)

            def filter_func(record):
                return (record["name"] + ".")[:length] == parent

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
            encoding = None

        if encoding is None:
            encoding = "ascii"

        with Logger._lock:
            handler_id = next(Logger._handlers_count)

            exception_formatter = ExceptionFormatter(
                colorize=colorize,
                encoding=encoding,
                diagnose=diagnose,
                backtrace=backtrace,
                hidden_frames_filename=self.catch.__code__.co_filename,
            )

            handler = Handler(
                name=name,
                writer=writer,
                stopper=stopper,
                levelno=levelno,
                formatter=formatter,
                is_formatter_dynamic=is_formatter_dynamic,
                filter_=filter_func,
                colorize=colorize,
                serialize=serialize,
                catch=catch,
                enqueue=enqueue,
                id_=handler_id,
                exception_formatter=exception_formatter,
                levels_ansi_codes=Logger._levels_ansi_codes,
            )

            handlers = Logger._handlers.copy()
            handlers[handler_id] = handler

            Logger._min_level = min(Logger._min_level, levelno)
            Logger._handlers = handlers

        return handler_id

    def __repr__(self):
        return "<loguru.logger handlers=%r>" % list(Logger._handlers.values())

    def remove(self, handler_id=None):
        """Remove a previously added handler and stop sending logs to its sink.

        Parameters
        ----------
        handler_id : |int| or ``None``
            The id of the sink to remove, as it was returned by the |add| method. If ``None``, all
            handlers are removed. The pre-configured handler is guaranteed to have the index ``0``.

        Raises
        ------
        ValueError
            If ``handler_id`` is not ``None`` but there is no active handler with such id.

        Examples
        --------
        >>> i = logger.add(sys.stderr, format="{message}")
        >>> logger.info("Logging")
        Logging
        >>> logger.remove(i)
        >>> logger.info("No longer logging")
        """
        with Logger._lock:
            handlers = Logger._handlers.copy()

            if handler_id is None:
                for handler in handlers.values():
                    handler.stop()
                handlers.clear()
            else:
                try:
                    handler = handlers.pop(handler_id)
                except KeyError:
                    raise ValueError("There is no existing handler with id '%s'" % handler_id)
                handler.stop()

            levelnos = (h.levelno for h in handlers.values())
            Logger._min_level = min(levelnos, default=float("inf"))
            Logger._handlers = handlers

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
        library from `@Qix-`_) depends on the ``diagnose`` option of each configured sink.

        The returned object can also be used as a context manager.

        Parameters
        ----------
        exception : |Exception|, optional
            The type of exception to intercept. If several types should be caught, a tuple of
            exceptions can be used too.
        level : |str| or |int|, optional
            The level name or severity with which the message should be logged.
        reraise : |bool|, optional
            Whether the exception should be raised again and hence propagated to the caller.
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
        Traceback (most recent call last):
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
            def __init__(self_, from_decorator):
                self_._from_decorator = from_decorator

            def __enter__(self_):
                return None

            def __exit__(self_, type_, value, traceback_):
                if type_ is None:
                    return

                if not issubclass(type_, exception):
                    return False

                from_decorator = self_._from_decorator
                _, depth, _, *options = self._options

                if from_decorator:
                    depth += 1

                catch_options = [(type_, value, traceback_), depth, True] + options
                level_id, static_level_no = self._dynamic_level(level)
                self._log(level_id, static_level_no, from_decorator, catch_options, message, (), {})

                return not reraise

            def __call__(_, function):
                catcher = Catcher(True)

                if inspect.iscoroutinefunction(function):

                    async def catch_wrapper(*args, **kwargs):
                        with catcher:
                            return await function(*args, **kwargs)

                elif inspect.isgeneratorfunction(function):

                    def catch_wrapper(*args, **kwargs):
                        with catcher:
                            return (yield from function(*args, **kwargs))

                else:

                    def catch_wrapper(*args, **kwargs):
                        with catcher:
                            return function(*args, **kwargs)

                functools.update_wrapper(catch_wrapper, function)
                return catch_wrapper

        return Catcher(False)

    def opt(self, *, exception=None, record=False, lazy=False, ansi=False, raw=False, depth=0):
        r"""Parametrize a logging call to slightly change generated log message.

        Parameters
        ----------
        exception : |bool|, |tuple| or |Exception|, optional
            If it does not evaluate as ``False``, the passed exception is formatted and added to the
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
            If ``True``, the formatting of each sink will be bypassed and the message will be sent
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
        return Logger(exception, depth, record, lazy, ansi, raw, *self._options[-2:])

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
        >>> logger.add(sys.stderr, format="{extra[ip]} - {message}")
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
        *options, extra = _self._options
        return Logger(*options, {**extra, **kwargs})

    def patch(self, patcher):
        """Attach a function to modify the record dict created by each logging call.

        The ``patcher`` may be used to update the record on-the-fly before it's propagated to the
        handlers. This allows the "extra" dict to be populated with dynamic values and also permits
        advanced modifications of the record emitted while logging a message. The function is called
        once before sending the log message to the different handlers.

        It is recommended to apply modification on the ``record["extra"]`` dict rather than on the
        ``record`` dict itself, as some values are used internally by Loguru, and modify them may
        produce unexpected results.

        Parameters
        ----------
        patcher: |function|_
            The function to which the record dict will be passed as the sole argument. This function
            is in charge of updating the record in-place, the function does not need to return any
            value, the modified record object will be re-used.

        Returns
        -------
        :class:`~Logger`
            A logger wrapping the core logger, but which records are passed through the ``patcher``
            function before being sent to the added handlers.

        Examples
        --------
        >>> logger.add(sys.stderr, format="{extra[utc]} {message}")
        >>> logger = logger.patch(lambda record: record["extra"].update(utc=datetime.utcnow())
        >>> logger.info("That's way, you can log messages with time displayed in UTC")

        >>> def wrapper(func):
        ...     @functools.wraps(func)
        ...     def wrapped(*args, **kwargs):
        ...         logger.patch(lambda r: r.update(function=func.__name__)).info("Wrapped!")
        ...         return func(*args, **kwargs)
        ...     return wrapped

        >>> def recv_record_from_network(pipe):
        ...     record = pickle.loads(pipe.read())
        ...     level, message = record["level"], record["message"]
        ...     logger.patch(lambda r: r.update(record)).log(level, message)
        """
        *options, _, extra = self._options
        return Logger(*options, patcher, extra)

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
        >>> logger.add(sys.stderr, format="{level.no} {icon} {message}")
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
                return Logger._levels[name]
            except KeyError:
                raise ValueError("Level '%s' does not exist" % name)

        if name not in Logger._levels:
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

        ansi = parse_ansi(color)
        level = Level(no, color, icon)

        with Logger._lock:
            Logger._levels[name] = level
            Logger._levels_ansi_codes[name] = ansi
            for handler in Logger._handlers.values():
                handler.update_format(name)

        return level

    def disable(self, name):
        """Disable logging of messages coming from ``name`` module and its children.

        Developers of library using `Loguru` should absolutely disable it to avoid disrupting
        users with unrelated logs messages.

        Note that in some rare circumstances, it is not possible for `Loguru` to
        determine the module's ``__name__`` value. In such situation, ``record["name"]`` will be
        equals to ``None``, this is why ``None`` is also a valid argument.

        Parameters
        ----------
        name : |str| or ``None``
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
        """Enable logging of messages coming from ``name`` module and its children.

        Logging is generally disabled by imported library using `Loguru`, hence this function
        allows users to receive these messages anyway.

        To enable all logs regardless of the module they are coming from, an empty string ``""`` can
        be passed.

        Parameters
        ----------
        name : |str| or ``None``
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

    def configure(self, *, handlers=None, levels=None, extra=None, patch=None, activation=None):
        """Configure the core logger.

        It should be noted that ``extra`` values set using this function are available across all
        modules, so this is the best way to set overall default values.

        Parameters
        ----------
        handlers : |list| of |dict|, optional
            A list of each handler to be added. The list should contain dicts of params passed to
            the |add| function as keyword arguments. If not ``None``, all previously added
            handlers are first removed.
        levels : |list| of |dict|, optional
            A list of each level to be added or updated. The list should contain dicts of params
            passed to the |level| function as keyword arguments. This will never remove previously
            created levels.
        extra : |dict|, optional
            A dict containing additional parameters bound to the core logger, useful to share
            common properties if you call |bind| in several of your files modules. If not ``None``,
            this will remove previously configured ``extra`` dict.
        patch : |function|_, optional
            A function that will be applied to the record dict of each logged messages across all
            modules using the logger. It should modify the dict in-place without returning anything.
            The function is executed prior to the one possibly added by the |patch| method. If not
            ``None``, this will replace previously configured ``patch`` function.
        activation : |list| of |tuple|, optional
            A list of ``(name, state)`` tuples which denotes which loggers should be enabled (if
            `state` is ``True``) or disabled (if `state` is ``False``). The calls to |enable|
            and |disable| are made accordingly to the list order. This will not modify previously
            activated loggers, so if you need a fresh start preprend your list with ``("", False)``
            or ``("", True)``.

        Returns
        -------
        :class:`list` of :class:`int`
            A list containing the identifiers of added sinks (if any).

        Examples
        --------
        >>> logger.configure(
        ...     handlers=[
        ...         dict(sink=sys.stderr, format="[{time}] {message}"),
        ...         dict(sink="file.log", enqueue=True, serialize=True),
        ...     ],
        ...     levels=[dict(name="NEW", no=13, icon="¤", color="")],
        ...     extra={"common_to_all": "default"},
        ...     patch=lambda record: record["extra"].update(some_value=42),
        ...     activation=[("my_module.secret", False), ("another_library.module", True)],
        ... )
        [1, 2]

        >>> # Set a default "extra" dict to logger across all modules, without "bind()"
        >>> extra = {"context": "foo"}
        >>> logger.configure(extra=extra)
        >>> logger.start(sys.stderr, format="{extra[context]} - {message}")
        >>> logger.info("Context without bind")
        >>> # => "foo - Context without bind"
        >>> logger.bind(context="bar").info("Suppress global context")
        >>> # => "bar - Suppress global context"
        """
        if handlers is not None:
            self.remove()
        else:
            handlers = []

        if levels is not None:
            for params in levels:
                self.level(**params)

        if patch is not None:
            with Logger._lock:
                Logger._patcher_class = patch

        if extra is not None:
            with Logger._lock:
                Logger._extra_class.clear()
                Logger._extra_class.update(extra)

        if activation is not None:
            for name, state in activation:
                if state:
                    self.enable(name)
                else:
                    self.disable(name)

        return [self.add(**params) for params in handlers]

    def _change_activation(self, name, status):
        if not (name is None or isinstance(name, str)):
            raise ValueError(
                "Invalid name, it should be a string (or ``None``), not: '%s'" % type(name).__name__
            )

        with Logger._lock:
            enabled = Logger._enabled.copy()

            if name is None:
                for n in enabled:
                    if n is None:
                        enabled[n] = status
                Logger._activation_none = status
                Logger._enabled = enabled
                return

            if name != "":
                name += "."

            activation_list = [(n, s) for n, s in Logger._activation_list if n[: len(name)] != name]

            parent_status = next((s for n, s in activation_list if name[: len(n)] == n), None)
            if parent_status != status and not (name == "" and status is True):
                activation_list.append((name, status))

                def modules_depth(x):
                    return x[0].count(".")

                activation_list.sort(key=modules_depth, reverse=True)

            for n in enabled:
                if n is not None and (n + ".")[: len(name)] == name:
                    enabled[n] = status

            Logger._activation_list = activation_list
            Logger._enabled = enabled

    @staticmethod
    def parse(file, pattern, *, cast={}, chunk=2 ** 16):
        """
        Parse raw logs and extract each entry as a |dict|.

        The logging format has to be specified as the regex ``pattern``, it will then be
        used to parse the ``file`` and retrieve each entry based on the named groups present
        in the regex.

        Parameters
        ----------
        file : |str|, |Path| or |file-like object|_
            The path of the log file to be parsed, or an already opened file object.
        pattern : |str| or |re.Pattern|_
            The regex to use for logs parsing, it should contain named groups which will be included
            in the returned dict.
        cast : |function|_ or |dict|, optional
            A function that should convert in-place the regex groups parsed (a dict of string
            values) to more appropriate types. If a dict is passed, it should be a mapping between
            keys of parsed log dict and the function that should be used to convert the associated
            value.
        chunk : |int|, optional
            The number of bytes read while iterating through the logs, this avoids having to load
            the whole file in memory.

        Yields
        ------
        :class:`dict`
            The dict mapping regex named groups to matched values, as returned by |match.groupdict|
            and optionally converted according to ``cast`` argument.

        Examples
        --------
        >>> reg = r"(?P<lvl>[0-9]+): (?P<msg>.*)"    # If log format is "{level.no} - {message}"
        >>> for e in logger.parse("file.log", reg):  # A file line could be "10 - A debug message"
        ...     print(e)                             # => {'lvl': '10', 'msg': 'A debug message'}
        ...

        >>> caster = dict(lvl=int)                   # Parse 'lvl' key as an integer
        >>> for e in logger.parse("file.log", reg, cast=caster):
        ...     print(e)                             # => {'lvl': 10, 'msg': 'A debug message'}

        >>> def cast(groups):
        ...     if "date" in groups:
        ...         groups["date"] = datetime.strptime(groups["date"], "%Y-%m-%d %H:%M:%S")
        ...
        >>> with open("file.log") as file:
        ...     for log in logger.parse(file, reg, cast=cast):
        ...         print(log["date"], log["something_else"])
        """
        if isinstance(file, (str, PathLike)):
            should_close = True
            fileobj = open(str(file))
        elif hasattr(file, "read") and callable(file.read):
            should_close = False
            fileobj = file
        else:
            raise ValueError(
                "Invalid file, it should be a string path or a file object, not: '%s'"
                % type(file).__name__
            )

        if isinstance(cast, dict):

            def cast_function(groups):
                for key, converter in cast.items():
                    if key in groups:
                        groups[key] = converter(groups[key])

        elif callable(cast):
            cast_function = cast
        else:
            raise ValueError(
                "Invalid cast, it should be a function or a dict, not: '%s'" % type(cast).__name__
            )

        try:
            regex = re.compile(pattern)
        except TypeError:
            raise ValueError(
                "Invalid pattern, it should be a string or a compiled regex, not: '%s'"
                % type(pattern).__name__
            )

        matches = Logger._find_iter(fileobj, regex, chunk)

        for match in matches:
            groups = match.groupdict()
            cast_function(groups)
            yield groups

        if should_close:
            fileobj.close()

    @staticmethod
    def _find_iter(fileobj, regex, chunk):
        buffer = fileobj.read(0)

        while 1:
            text = fileobj.read(chunk)
            buffer += text
            matches = list(regex.finditer(buffer))

            if not text:
                yield from matches
                break

            if len(matches) > 1:
                end = matches[-2].end()
                buffer = buffer[end:]
                yield from matches[:-1]

    @staticmethod
    def _log(level_id, static_level_no, from_decorator, options, message, args, kwargs):
        if not Logger._handlers:
            return

        (exception, depth, record, lazy, ansi, raw, patcher, extra) = options

        frame = get_frame(depth + 2)

        try:
            name = frame.f_globals["__name__"]
        except KeyError:
            name = None

        try:
            if not Logger._enabled[name]:
                return
        except KeyError:
            enabled = Logger._enabled
            if name is None:
                status = Logger._activation_none
                enabled[name] = status
                if not status:
                    return
            else:
                dotted_name = name + "."
                for dotted_module_name, status in Logger._activation_list:
                    if dotted_name[: len(dotted_module_name)] == dotted_module_name:
                        if status:
                            break
                        enabled[name] = False
                        return
                enabled[name] = True

        current_datetime = aware_now()

        if level_id is None:
            level_icon = " "
            level_no = static_level_no
            level_name = "Level %d" % level_no
        else:
            try:
                level_no, _, level_icon = Logger._levels[level_id]
                level_name = level_id
            except KeyError:
                raise ValueError("Level '%s' does not exist" % level_id)

        if level_no < Logger._min_level:
            return

        code = frame.f_code
        file_path = code.co_filename
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

        if exception:
            if isinstance(exception, BaseException):
                type_, value, traceback = (type(exception), exception, exception.__traceback__)
            elif isinstance(exception, tuple):
                type_, value, traceback = exception
            else:
                type_, value, traceback = sys.exc_info()
            exception = ExceptionRecattr(type_, value, traceback)
        else:
            exception = None

        log_record = {
            "elapsed": elapsed,
            "exception": exception,
            "extra": {**Logger._extra_class, **extra},
            "file": file_recattr,
            "function": code.co_name,
            "level": level_recattr,
            "line": frame.f_lineno,
            "message": message,
            "module": splitext(file_name)[0],
            "name": name,
            "process": process_recattr,
            "thread": thread_recattr,
            "time": current_datetime,
        }

        if lazy:
            args = [arg() for arg in args]
            kwargs = {key: value() for key, value in kwargs.items()}

        if record:
            log_record["message"] = message.format(*args, **kwargs, record=log_record)
        elif args or kwargs:
            log_record["message"] = message.format(*args, **kwargs)

        if Logger._patcher_class:
            Logger._patcher_class(log_record)

        if patcher:
            patcher(log_record)

        for handler in Logger._handlers.values():
            handler.emit(log_record, level_id, from_decorator, ansi, raw)

    def trace(_self, _message, *args, **kwargs):
        r"""Log ``_message.format(*args, **kwargs)`` with severity ``'TRACE'``."""
        _self._log("TRACE", None, False, _self._options, _message, args, kwargs)

    def debug(_self, _message, *args, **kwargs):
        r"""Log ``_message.format(*args, **kwargs)`` with severity ``'DEBUG'``."""
        _self._log("DEBUG", None, False, _self._options, _message, args, kwargs)

    def info(_self, _message, *args, **kwargs):
        r"""Log ``_message.format(*args, **kwargs)`` with severity ``'INFO'``."""
        _self._log("INFO", None, False, _self._options, _message, args, kwargs)

    def success(_self, _message, *args, **kwargs):
        r"""Log ``_message.format(*args, **kwargs)`` with severity ``'SUCCESS'``."""
        _self._log("SUCCESS", None, False, _self._options, _message, args, kwargs)

    def warning(_self, _message, *args, **kwargs):
        r"""Log ``_message.format(*args, **kwargs)`` with severity ``'WARNING'``."""
        _self._log("WARNING", None, False, _self._options, _message, args, kwargs)

    def error(_self, _message, *args, **kwargs):
        r"""Log ``_message.format(*args, **kwargs)`` with severity ``'ERROR'``."""
        _self._log("ERROR", None, False, _self._options, _message, args, kwargs)

    def critical(_self, _message, *args, **kwargs):
        r"""Log ``_message.format(*args, **kwargs)`` with severity ``'CRITICAL'``."""
        _self._log("CRITICAL", None, False, _self._options, _message, args, kwargs)

    def exception(_self, _message, *args, **kwargs):
        r"""Convenience method for logging an ``'ERROR'`` with exception information."""
        options = (True,) + _self._options[1:]
        _self._log("ERROR", None, False, options, _message, args, kwargs)

    def log(_self, _level, _message, *args, **kwargs):
        r"""Log ``_message.format(*args, **kwargs)`` with severity ``_level``."""
        level_id, static_level_no = _self._dynamic_level(_level)
        _self._log(level_id, static_level_no, False, _self._options, _message, args, kwargs)

    @staticmethod
    @functools.lru_cache(maxsize=32)
    def _dynamic_level(level):

        if isinstance(level, str):
            return (level, None)

        if isinstance(level, int):
            if level < 0:
                raise ValueError(
                    "Invalid level value, it should be a positive integer, not: %d" % level
                )
            return (None, level)

        raise ValueError(
            "Invalid level, it should be an integer or a string, not: '%s'" % type(level).__name__
        )

    def start(self, *args, **kwargs):
        """Deprecated function to |add| a new handler.

        Warnings
        --------
        .. deprecated:: 0.2.2
          ``start()`` will be removed in Loguru 1.0.0, it is replaced by ``add()`` which is a less
          confusing name.
        """
        warnings.warn(
            "The 'start()' method is deprecated, please use 'add()' instead", DeprecationWarning
        )
        return self.add(*args, **kwargs)

    def stop(self, *args, **kwargs):
        """Deprecated function to |remove| an existing handler.

        Warnings
        --------
        .. deprecated:: 0.2.2
          ``stop()`` will be removed in Loguru 1.0.0, it is replaced by ``remove()`` which is a less
          confusing name.
        """
        warnings.warn(
            "The 'stop()' method is deprecated, please use 'remove()' instead", DeprecationWarning
        )
        return self.remove(*args, **kwargs)
