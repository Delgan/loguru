`Unreleased`_
=============

- Add new ``logger.reinstall()`` method to automatically set up the ``logger`` in spawned child processes (`#818 <https://github.com/Delgan/loguru/issues/818>`_, thanks `@monchin <https://github.com/monchin>`_).
- Fix a regression preventing formatting of ``record["time"]`` when using ``zoneinfo.ZoneInfo`` timezones (`#1260 <https://github.com/Delgan/loguru/pull/1260>`_, thanks `@bijlpieter <https://github.com/bijlpieter>`_).
- Fix possible ``ValueError`` raised on Windows when system clock was set far ahead in the future (`#1291 <https://github.com/Delgan/loguru/issues/1291>`_).
- Allow the ``rotation`` argument of file sinks to accept a list of rotation conditions, any of which can trigger the rotation (`#1174 <https://github.com/Delgan/loguru/issues/1174>`_, thanks `@CollinHeist <https://github.com/CollinHeist>`_).
- Update the default log format to include the timezone offset since it produces less ambiguous logs (`#856 <https://github.com/Delgan/loguru/pull/856>`_, thanks `@tim-x-y-z <https://github.com/tim-x-y-z>`_).
- Honor the ``NO_COLOR`` environment variable which disables color output by default if ``colorize`` is not provided (`#1178 <https://github.com/Delgan/loguru/issues/1178>`_).
- Honor the ``FORCE_COLOR`` environment variable which enables color output by default if ``colorize`` is not provided (`#1305 <https://github.com/Delgan/loguru/issues/1305>`_, thanks `@nhurden <https://github.com/nhurden>`_).
- Add requirement for ``TERM`` environment variable not to be ``"dumb"`` to enable colorization (`#1287 <https://github.com/Delgan/loguru/pull/1287>`_, thanks `@snosov1 <https://github.com/snosov1>`_).
- Make ``logger.catch()`` usable as an asynchronous context manager (`#1084 <https://github.com/Delgan/loguru/issues/1084>`_).
- Make ``logger.catch()`` compatible with asynchronous generators (`#1302 <https://github.com/Delgan/loguru/issues/1302>`_).


`0.7.3`_ (2024-12-06)
=====================

- Fix Cython incompatibility caused by the absence of underlying stack frames, which resulted in a ``ValueError`` during logging (`#88 <https://github.com/Delgan/loguru/issues/88>`_).
- Fix possible ``RuntimeError`` when removing all handlers with ``logger.remove()`` due to thread-safety issue (`#1183 <https://github.com/Delgan/loguru/issues/1183>`_, thanks `@jeremyk <https://github.com/jeremyk>`_).
- Fix ``diagnose=True`` option of exception formatting not working as expected with Python 3.13 (`#1235 <https://github.com/Delgan/loguru/issues/1235>`_, thanks `@etianen <https://github.com/etianen>`_).
- Fix non-standard level names not fully compatible with ``logging.Formatter()`` (`#1231 <https://github.com/Delgan/loguru/issues/1231>`_, thanks `@yechielb2000 <https://github.com/yechielb2000>`_).
- Fix inability to display a literal ``"\"`` immediately before color markups (`#988 <https://github.com/Delgan/loguru/issues/988>`_).
- Fix possible infinite recursion when an exception is raised from a ``__repr__``  method decorated with ``logger.catch()`` (`#1044 <https://github.com/Delgan/loguru/issues/1044>`_).
- Improve performance of ``datetime`` formatting while logging messages (`#1201 <https://github.com/Delgan/loguru/issues/1201>`_, thanks `@trim21 <https://github.com/trim21>`_).
- Reduce startup time in the presence of installed but unused ``IPython`` third-party library (`#1001 <https://github.com/Delgan/loguru/issues/1001>`_, thanks `@zakstucke <https://github.com/zakstucke>`_).


`0.7.2`_ (2023-09-11)
=====================

- Add support for formatting of ``ExceptionGroup`` errors (`#805 <https://github.com/Delgan/loguru/issues/805>`_).
- Fix possible ``RuntimeError`` when using ``multiprocessing.set_start_method()`` after importing the ``logger`` (`#974 <https://github.com/Delgan/loguru/issues/974>`_).
- Fix formatting of possible ``__notes__`` attached to an ``Exception`` (`#980 <https://github.com/Delgan/loguru/issues/980>`_).


`0.7.1`_ (2023-09-04)
=====================

- Add a new ``context`` optional argument to ``logger.add()`` specifying ``multiprocessing`` context (like ``"spawn"`` or ``"fork"``) to be used internally instead of the default one (`#851 <https://github.com/Delgan/loguru/issues/851>`_).
- Add support for true colors on Windows using ANSI/VT console when available (`#934 <https://github.com/Delgan/loguru/issues/934>`_, thanks `@tunaflsh <https://github.com/tunaflsh>`_).
- Fix possible deadlock when calling ``logger.complete()`` with concurrent logging of an asynchronous sink (`#906 <https://github.com/Delgan/loguru/issues/906>`_).
- Fix file possibly rotating too early or too late when re-starting an application around midnight (`#894 <https://github.com/Delgan/loguru/issues/894>`_).
- Fix inverted ``"<hide>"`` and ``"<strike>"`` color tags (`#943 <https://github.com/Delgan/loguru/pull/943>`_, thanks `@tunaflsh <https://github.com/tunaflsh>`_).
- Fix possible untraceable errors raised when logging non-unpicklable ``Exception`` instances while using ``enqueue=True`` (`#329 <https://github.com/Delgan/loguru/issues/329>`_).
- Fix possible errors raised when logging non-picklable ``Exception`` instances while using ``enqueue=True`` (`#342 <https://github.com/Delgan/loguru/issues/342>`_, thanks `@ncoudene <https://github.com/ncoudene>`_).
- Fix missing seconds and microseconds when formatting timezone offset that requires such accuracy (`#961 <https://github.com/Delgan/loguru/issues/961>`_).
- Raise ``ValueError`` if an attempt to use nanosecond precision for time formatting is detected (`#855 <https://github.com/Delgan/loguru/issues/855>`_).


`0.7.0`_ (2023-04-10)
=====================

- Update ``InterceptHandler`` recipe to make it compatible with Python 3.11 (`#654 <https://github.com/Delgan/loguru/issues/654>`_).
- Add a new ``watch`` optional argument to file sinks in order to automatically re-create possibly deleted or changed file (`#471 <https://github.com/Delgan/loguru/issues/471>`_).
- Make ``patch()`` calls cumulative instead of overriding the possibly existing patching function (`#462 <https://github.com/Delgan/loguru/issues/462>`_).
- Make sinks added with ``enqueue=True`` and ``catch=False`` still process logged messages in case of internal exception (`#833 <https://github.com/Delgan/loguru/issues/833>`_).
- Avoid possible deadlocks caused by re-using the logger inside a sink, a signal handler or a ``__del__`` method. Since the logger is not re-entrant, such misuse will be detected and will now generate a ``RuntimeError`` (`#712 <https://github.com/Delgan/loguru/issues/712>`_, thanks `@jacksmith15 <https://github.com/jacksmith15>`_).
- Fix file sink rotation using an aware ``datetime.time`` for which the timezone was ignored (`#697 <https://github.com/Delgan/loguru/issues/697>`_).
- Fix logs colorization not automatically enabled for Jupyter Notebook and Google Colab (`#494 <https://github.com/Delgan/loguru/issues/494>`_).
- Fix logs colorization not automatically enabled for Github Actions and others CI platforms (`#604 <https://github.com/Delgan/loguru/issues/604>`_).
- Fix ``logger.complete()`` possibly hanging forever when ``enqueue=True`` and ``catch=False`` if internal thread killed due to ``Exception`` raised by sink (`#647 <https://github.com/Delgan/loguru/issues/647>`_).
- Fix incompatibility with ``freezegun`` library used to simulate time (`#600 <https://github.com/Delgan/loguru/issues/600>`_).
- Raise exception if ``logger.catch()`` is used to wrap a class instead of a function to avoid unexpected behavior (`#623 <https://github.com/Delgan/loguru/issues/623>`_).


`0.6.0`_ (2022-01-29)
=====================

- Remove internal use of ``pickle.loads()`` to fix the (finally rejected) security vulnerability referenced as `CVE-2022-0329 <https://nvd.nist.gov/vuln/detail/CVE-2022-0329>`_ (`#563 <https://github.com/Delgan/loguru/issues/563>`_).
- Modify coroutine sink to make it discard log messages when ``loop=None`` and no event loop is running (due to internally using ``asyncio.get_running_loop()`` in place of ``asyncio.get_event_loop()``).
- Remove the possibility to add a coroutine sink with ``enqueue=True`` if ``loop=None`` and no event loop is running.
- Change default encoding of file sink to be ``utf8`` instead of ``locale.getpreferredencoding()`` (`#339 <https://github.com/Delgan/loguru/issues/339>`_).
- Prevent non-ascii characters to be escaped while logging JSON message with ``serialize=True`` (`#575 <https://github.com/Delgan/loguru/pull/575>`_, thanks `@ponponon <https://github.com/ponponon>`_).
- Fix ``flake8`` errors and improve code readability (`#353 <https://github.com/Delgan/loguru/issues/353>`_, thanks `@AndrewYakimets <https://github.com/AndrewYakimets>`_).


`0.5.3`_ (2020-09-20)
=====================

- Fix child process possibly hanging at exit while combining ``enqueue=True`` with third party library like ``uwsgi`` (`#309 <https://github.com/Delgan/loguru/issues/309>`_, thanks `@dstlmrk <https://github.com/dstlmrk>`_).
- Fix possible exception during formatting of non-string messages (`#331 <https://github.com/Delgan/loguru/issues/331>`_).


`0.5.2`_ (2020-09-06)
=====================

- Fix ``AttributeError`` within handlers using ``serialize=True`` when calling ``logger.exception()`` outside of the context of an exception (`#296 <https://github.com/Delgan/loguru/issues/296>`_).
- Fix error while logging an exception containing a non-picklable ``value`` to a handler with ``enqueue=True`` (`#298 <https://github.com/Delgan/loguru/issues/298>`_).
- Add support for async callable classes (with ``__call__`` method) used as sinks (`#294 <https://github.com/Delgan/loguru/pull/294>`_, thanks `@jessekrubin <https://github.com/jessekrubin>`_).


`0.5.1`_ (2020-06-12)
=====================

- Modify the way the ``extra`` dict is used by ``LogRecord`` in order to prevent possible ``KeyError`` with standard ``logging`` handlers (`#271 <https://github.com/Delgan/loguru/issues/271>`_).
- Add a new ``default`` optional argument to ``logger.catch()``, it should be the returned value by the decorated function in case an error occurred (`#272 <https://github.com/Delgan/loguru/issues/272>`_).
- Fix ``ValueError`` when using ``serialize=True`` in combination with ``logger.catch()`` or ``logger.opt(record=True)`` due to circular reference of the ``record`` dict (`#286 <https://github.com/Delgan/loguru/issues/286>`_).


`0.5.0`_ (2020-05-17)
=====================

- Remove the possibility to modify the severity ``no`` of levels once they have been added in order to prevent surprising behavior (`#209 <https://github.com/Delgan/loguru/issues/209>`_).
- Add better support for "structured logging" by automatically adding ``**kwargs`` to the ``extra`` dict besides using these arguments to format the message. This behavior can be disabled by setting the new ``.opt(capture=False)`` parameter (`#2 <https://github.com/Delgan/loguru/issues/2>`_).
- Add a new ``onerror`` optional argument to ``logger.catch()``, it should be a function which will be called when an exception occurs in order to customize error handling (`#224 <https://github.com/Delgan/loguru/issues/224>`_).
- Add a new ``exclude`` optional argument to ``logger.catch()``, is should be a type of exception to be purposefully ignored and propagated to the caller without being logged (`#248 <https://github.com/Delgan/loguru/issues/248>`_).
- Modify ``complete()`` to make it callable from non-asynchronous functions, it can thus be used if ``enqueue=True`` to make sure all messages have been processed (`#231 <https://github.com/Delgan/loguru/issues/231>`_).
- Fix possible deadlocks on Linux when ``multiprocessing.Process()`` collides with ``enqueue=True`` or ``threading`` (`#231 <https://github.com/Delgan/loguru/issues/231>`_).
- Fix ``compression`` function not executable concurrently due to file renaming (to resolve conflicts) being performed after and not before it (`#243 <https://github.com/Delgan/loguru/issues/243>`_).
- Fix the filter function listing files for ``retention`` being too restrictive, it now matches files based on the pattern ``"root(.*).ext(.*)"`` (`#229 <https://github.com/Delgan/loguru/issues/229>`_).
- Fix the impossibility to ``remove()`` a handler if an exception is raised while the sink' ``stop()`` function is called (`#237 <https://github.com/Delgan/loguru/issues/237>`_).
- Fix file sink left in an unstable state if an exception occurred during ``retention`` or ``compression`` process (`#238 <https://github.com/Delgan/loguru/issues/238>`_).
- Fix situation where changes made to ``record["message"]`` were unexpectedly ignored when ``opt(colors=True)``, causing "out-of-date" ``message`` to be logged due to implementation details (`#221 <https://github.com/Delgan/loguru/issues/221>`_).
- Fix possible exception if a stream having an ``isatty()`` method returning ``True`` but not being compatible with ``colorama`` is used on Windows (`#249 <https://github.com/Delgan/loguru/issues/249>`_).
- Fix exceptions occurring in coroutine sinks never retrieved and hence causing warnings (`#227 <https://github.com/Delgan/loguru/issues/227>`_).


`0.4.1`_ (2020-01-19)
=====================

- Deprecate the ``ansi`` parameter of ``.opt()`` in favor of ``colors`` which is a name more appropriate.
- Prevent unrelated files and directories to be incorrectly collected thus causing errors during the ``retention`` process (`#195 <https://github.com/Delgan/loguru/issues/195>`_, thanks `@gazpachoking <https://github.com/gazpachoking>`_).
- Strip color markups contained in ``record["message"]`` when logging with ``.opt(ansi=True)`` instead of leaving them as is (`#198 <https://github.com/Delgan/loguru/issues/198>`_).
- Ignore color markups contained in ``*args`` and ``**kwargs`` when logging with ``.opt(ansi=True)``, leave them as is instead of trying to use them to colorize the message which could cause undesirable errors (`#197 <https://github.com/Delgan/loguru/issues/197>`_).


`0.4.0`_ (2019-12-02)
=====================

- Add support for coroutine functions used as sinks and add the new ``logger.complete()`` asynchronous method to ``await`` them (`#171 <https://github.com/Delgan/loguru/issues/171>`_).
- Add a way to filter logs using one level per module in the form of a ``dict`` passed to the ``filter`` argument (`#148 <https://github.com/Delgan/loguru/issues/148>`_).
- Add type hints to annotate the public methods using a ``.pyi`` stub file (`#162 <https://github.com/Delgan/loguru/issues/162>`_).
- Add support for ``copy.deepcopy()`` of the ``logger`` allowing multiple independent loggers with separate set of handlers (`#72 <https://github.com/Delgan/loguru/issues/72>`_).
- Add the possibility to convert ``datetime`` to UTC before formatting (in logs and filenames) by adding ``"!UTC"`` at the end of the time format specifier (`#128 <https://github.com/Delgan/loguru/issues/128>`_).
- Add the level ``name`` as the first argument of namedtuple returned by the ``.level()`` method.
- Remove ``class`` objects from the list of supported sinks and restrict usage of ``**kwargs`` in ``.add()`` to file sink only. User is in charge of instantiating sink and wrapping additional keyword arguments if needed, before passing it to the ``.add()`` method.
- Rename the ``logger.configure()`` keyword argument ``patch`` to ``patcher`` so it better matches the signature of ``logger.patch()``.
- Fix incompatibility with ``multiprocessing`` on Windows by entirely refactoring the internal structure of the ``logger`` so it can be inherited by child processes along with added handlers (`#108 <https://github.com/Delgan/loguru/issues/108>`_).
- Fix ``AttributeError`` while using a file sink on some distributions (like Alpine Linux) missing the ``os.getxattr`` and ``os.setxattr`` functions (`#158 <https://github.com/Delgan/loguru/pull/158>`_, thanks `@joshgordon <https://github.com/joshgordon>`_).
- Fix values wrongly displayed for keyword arguments during exception formatting with ``diagnose=True`` (`#144 <https://github.com/Delgan/loguru/issues/144>`_).
- Fix logging messages wrongly chopped off at the end while using standard ``logging.Handler`` sinks with ``.opt(raw=True)`` (`#136 <https://github.com/Delgan/loguru/issues/136>`_).
- Fix potential errors during rotation if destination file exists due to large resolution clock on Windows (`#179 <https://github.com/Delgan/loguru/issues/179>`_).
- Fix an error using a ``filter`` function "by name" while receiving a log with ``record["name"]`` equals to ``None``.
- Fix incorrect record displayed while handling errors (if ``catch=True``) occurring because of non-picklable objects (if ``enqueue=True``).
- Prevent hypothetical ``ImportError`` if a Python installation is missing the built-in ``distutils`` module (`#118 <https://github.com/Delgan/loguru/issues/118>`_).
- Raise ``TypeError`` instead of ``ValueError`` when a ``logger`` method is called with argument of invalid type.
- Raise ``ValueError`` if the built-in ``format()`` and ``filter()`` functions are respectively used as ``format`` and ``filter`` arguments of the ``add()`` method. This helps the user to understand the problem, as such a mistake can quite easily occur (`#177 <https://github.com/Delgan/loguru/issues/177>`_).
- Remove inheritance of some record dict attributes to ``str`` (for ``"level"``, ``"file"``, ``"thread"`` and ``"process"``).
- Give a name to the worker thread used when ``enqueue=True`` (`#174 <https://github.com/Delgan/loguru/pull/174>`_, thanks `@t-mart <https://github.com/t-mart>`_).


`0.3.2`_ (2019-07-21)
=====================

- Fix exception during import when executing Python with ``-s`` and ``-S`` flags causing ``site.USER_SITE`` to be missing (`#114 <https://github.com/Delgan/loguru/issues/114>`_).


`0.3.1`_ (2019-07-13)
=====================

- Fix ``retention`` and ``rotation`` issues when file sink initialized with ``delay=True`` (`#113 <https://github.com/Delgan/loguru/issues/113>`_).
- Fix ``"sec"`` no longer recognized as a valid duration unit for file ``rotation`` and ``retention`` arguments.
- Ensure stack from the caller is displayed while formatting exception of a function decorated with ``@logger.catch`` when ``backtrace=False``.
- Modify datetime used to automatically rename conflicting file when rotating (it happens if file already exists because ``"{time}"`` not presents in filename) so it's based on the file creation time rather than the current time.


`0.3.0`_ (2019-06-29)
=====================

- Remove all dependencies previously needed by ``loguru`` (on Windows platform, it solely remains ``colorama`` and ``win32-setctime``).
- Add a new ``logger.patch()`` method which can be used to modify the record dict on-the-fly before it's being sent to the handlers.
- Modify behavior of sink option ``backtrace`` so it only extends the stacktrace upward, the display of variables values is now controlled with the new ``diagnose`` argument (`#49 <https://github.com/Delgan/loguru/issues/49>`_).
- Change behavior of ``rotation`` option in file sinks: it is now based on the file creation time rather than the current time, note that proper support may differ depending on your platform (`#58 <https://github.com/Delgan/loguru/issues/58>`_).
- Raise errors on unknowns color tags rather than silently ignoring them (`#57 <https://github.com/Delgan/loguru/issues/57>`_).
- Add the possibility to auto-close color tags by using ``</>`` (e.g. ``<yellow>message</>``).
- Add coloration of exception traceback even if ``diagnose`` and ``backtrace`` options are ``False``.
- Add a way to limit the depth of formatted exceptions traceback by setting the conventional ``sys.tracebacklimit`` variable (`#77 <https://github.com/Delgan/loguru/issues/77>`_).
- Add ``__repr__`` value to the ``logger`` for convenient debugging (`#84 <https://github.com/Delgan/loguru/issues/84>`_).
- Remove colors tags mixing directives (e.g. ``<red,blue>``) for simplification.
- Make the ``record["exception"]`` attribute unpackable as a ``(type, value, traceback)`` tuple.
- Fix error happening in some rare circumstances because ``frame.f_globals`` dict did not contain ``"__name__"`` key and hence prevented Loguru to retrieve the module's name. From now, ``record["name"]`` will be equal to ``None`` in such case (`#62 <https://github.com/Delgan/loguru/issues/62>`_).
- Fix logging methods not being serializable with ``pickle`` and hence raising exception while being passed to some ``multiprocessing`` functions (`#102 <https://github.com/Delgan/loguru/issues/102>`_).
- Fix exception stack trace not colorizing source code lines on Windows.
- Fix possible ``AttributeError`` while formatting exceptions within a ``celery`` task (`#52 <https://github.com/Delgan/loguru/issues/52>`_).
- Fix ``logger.catch`` decorator not working with generator and coroutine functions (`#75 <https://github.com/Delgan/loguru/issues/75>`_).
- Fix ``record["path"]`` case being normalized for no necessary reason (`#85 <https://github.com/Delgan/loguru/issues/85>`_).
- Fix some Windows terminal emulators (mintty) not correctly detected as supporting colors, causing ansi codes to be automatically stripped (`#104 <https://github.com/Delgan/loguru/issues/104>`_).
- Fix handler added with ``enqueue=True`` stopping working if exception was raised in sink although ``catch=True``.
- Fix thread-safety of ``enable()`` and ``disable()`` being called during logging.
- Use Tox to run tests (`#41 <https://github.com/Delgan/loguru/issues/41>`_).


`0.2.5`_ (2019-01-20)
=====================

- Modify behavior of sink option ``backtrace=False`` so it doesn't extend traceback upward automatically (`#30 <https://github.com/Delgan/loguru/issues/30>`_).
- Fix import error on some platforms using Python 3.5 with limited ``localtime()`` support (`#33 <https://github.com/Delgan/loguru/issues/33>`_).
- Fix incorrect time formatting of locale month using ``MMM`` and ``MMMM`` tokens (`#34 <https://github.com/Delgan/loguru/pull/34>`_, thanks `@nasyxx <https://github.com/nasyxx>`_).
- Fix race condition permitting writing on a stopped handler.


`0.2.4`_ (2018-12-26)
=====================

- Fix adding handler while logging which was not thread-safe (`#22 <https://github.com/Delgan/loguru/issues/22>`_).


`0.2.3`_ (2018-12-16)
=====================

- Add support for PyPy.
- Add support for Python 3.5.
- Fix incompatibility with ``awscli`` by downgrading required ``colorama`` dependency version (`#12 <https://github.com/Delgan/loguru/issues/12>`_).


`0.2.2`_ (2018-12-12)
=====================

- Deprecate ``logger.start()`` and ``logger.stop()`` methods in favor of ``logger.add()`` and ``logger.remove()`` (`#3 <https://github.com/Delgan/loguru/issues/3>`_).
- Fix ignored formatting while using ``logging.Handler`` sinks (`#4 <https://github.com/Delgan/loguru/issues/4>`_).
- Fix impossibility to set empty environment variable color on Windows (`#7 <https://github.com/Delgan/loguru/issues/7>`_).


`0.2.1`_ (2018-12-08)
=====================

- Fix typo preventing README to be correctly displayed on PyPI.


`0.2.0`_ (2018-12-08)
=====================

- Remove the ``parser`` and refactor it into the ``logger.parse()`` method.
- Remove the ``notifier`` and its dependencies (``pip install notifiers`` should be used instead).


`0.1.0`_ (2018-12-07)
=====================

- Add logger.
- Add notifier.
- Add parser.


`0.0.1`_ (2017-09-04)
=====================

Initial release.


.. _Unreleased: https://github.com/delgan/loguru/compare/0.7.3...master
.. _0.7.3: https://github.com/delgan/loguru/releases/tag/0.7.3
.. _0.7.2: https://github.com/delgan/loguru/releases/tag/0.7.2
.. _0.7.1: https://github.com/delgan/loguru/releases/tag/0.7.1
.. _0.7.0: https://github.com/delgan/loguru/releases/tag/0.7.0
.. _0.6.0: https://github.com/delgan/loguru/releases/tag/0.6.0
.. _0.5.3: https://github.com/delgan/loguru/releases/tag/0.5.3
.. _0.5.2: https://github.com/delgan/loguru/releases/tag/0.5.2
.. _0.5.1: https://github.com/delgan/loguru/releases/tag/0.5.1
.. _0.5.0: https://github.com/delgan/loguru/releases/tag/0.5.0
.. _0.4.1: https://github.com/delgan/loguru/releases/tag/0.4.1
.. _0.4.0: https://github.com/delgan/loguru/releases/tag/0.4.0
.. _0.3.2: https://github.com/delgan/loguru/releases/tag/0.3.2
.. _0.3.1: https://github.com/delgan/loguru/releases/tag/0.3.1
.. _0.3.0: https://github.com/delgan/loguru/releases/tag/0.3.0
.. _0.2.5: https://github.com/delgan/loguru/releases/tag/0.2.5
.. _0.2.4: https://github.com/delgan/loguru/releases/tag/0.2.4
.. _0.2.3: https://github.com/delgan/loguru/releases/tag/0.2.3
.. _0.2.2: https://github.com/delgan/loguru/releases/tag/0.2.2
.. _0.2.1: https://github.com/delgan/loguru/releases/tag/0.2.1
.. _0.2.0: https://github.com/delgan/loguru/releases/tag/0.2.0
.. _0.1.0: https://github.com/delgan/loguru/releases/tag/0.1.0
.. _0.0.1: https://github.com/delgan/loguru/releases/tag/0.0.1
