Code snippets and recipes for ``loguru``
========================================

.. highlight:: python3

.. |print| replace:: :func:`print()`
.. |open| replace:: :func:`open()`
.. |sys.__stdout__| replace:: :data:`sys.__stdout__`
.. |sys.stdout| replace:: :data:`sys.stdout`
.. |sys.stderr| replace:: :data:`sys.stderr`
.. |warnings| replace:: :mod:`warnings`
.. |warnings.showwarning| replace:: :func:`warnings.showwarning`
.. |warnings.warn| replace:: :func:`warnings.warn`
.. |contextlib.redirect_stdout| replace:: :func:`contextlib.redirect_stdout`
.. |copy.deepcopy| replace:: :func:`copy.deepcopy`
.. |os.fork| replace:: :func:`os.fork`
.. |multiprocessing| replace:: :mod:`multiprocessing`
.. |traceback| replace:: :mod:`traceback`
.. |Thread| replace:: :class:`~threading.Thread`
.. |Process| replace:: :class:`~multiprocessing.Process`
.. |Pool| replace:: :class:`~multiprocessing.pool.Pool`
.. |Pool.map| replace:: :meth:`~multiprocessing.pool.Pool.map`
.. |Pool.apply| replace:: :meth:`~multiprocessing.pool.Pool.apply`
.. |sys.stdout.reconfigure| replace:: :meth:`sys.stdout.reconfigure() <io.TextIOWrapper.reconfigure>`
.. |UnicodeEncodeError| replace:: :exc:`UnicodeEncodeError`

.. |add| replace:: :meth:`~loguru._logger.Logger.add()`
.. |remove| replace:: :meth:`~loguru._logger.Logger.remove()`
.. |enable| replace:: :meth:`~loguru._logger.Logger.enable()`
.. |disable| replace:: :meth:`~loguru._logger.Logger.disable()`
.. |bind| replace:: :meth:`~loguru._logger.Logger.bind()`
.. |patch| replace:: :meth:`~loguru._logger.Logger.patch()`
.. |opt| replace:: :meth:`~loguru._logger.Logger.opt()`
.. |log| replace:: :meth:`~loguru._logger.Logger.log()`
.. |level| replace:: :meth:`~loguru._logger.Logger.level()`
.. |configure| replace:: :meth:`~loguru._logger.Logger.configure()`
.. |complete| replace:: :meth:`~loguru._logger.Logger.complete()`

.. _`unicode`: https://docs.python.org/3/howto/unicode.html

.. |stackprinter| replace:: ``stackprinter``
.. _stackprinter: https://github.com/cknd/stackprinter

.. |zmq| replace:: ``zmq``
.. _zmq: https://github.com/zeromq/pyzmq

.. _`GH#88`: https://github.com/Delgan/loguru/issues/88
.. _`GH#132`: https://github.com/Delgan/loguru/issues/132

Changing the level of an existing handler
-----------------------------------------

Once a handler has been added, it is actually not possible to update it. This is a deliberate choice in order to keep the Loguru's API minimal. Several solutions are possible, tough, if you need to change the configured ``level`` of a handler. Chose the one that best fits your use case.

The most straightforward workaround is to |remove| your handler and then re-|add| it with the updated ``level`` parameter. To do so, you have to keep a reference to the identifier number returned while adding a handler::

    handler_id = logger.add(sys.stderr, level="WARNING")

    logger.info("Logging 'WARNING' or higher messages only")

    ...

    logger.remove(handler_id)
    logger.add(sys.stderr, level="DEBUG")

    logger.debug("Logging 'DEBUG' messages too")


Alternatively, you can combine the |bind| method with the ``filter`` argument to provide a function dynamically filtering logs based on their level::

    def my_filter(record):
        if record["extra"].get("warn_only"):  # "warn_only" is bound to the logger and set to 'True'
            return record["level"].no >= logger.level("WARNING").no
        return True  # Fallback to default 'level' configured while adding the handler


    logger.add(sys.stderr, filter=my_filter, level="DEBUG")

    # Use this logger first, debug messages are filtered out
    logger = logger.bind(warn_only=True)
    logger.warn("Initialization in progress")

    # Then you can use this one to log all messages
    logger = logger.bind(warn_only=False)
    logger.debug("Back to debug messages")


Finally, more advanced control over handler's level can be achieved by using a callable object as the ``filter``::

    class MyFilter:

        def __init__(self, level):
            self.level = level

        def __call__(self, record):
            levelno = logger.level(self.level).no
            return record["level"].no >= levelno

    my_filter = MyFilter("WARNING")
    logger.add(sys.stderr, filter=my_filter, level=0)

    logger.warning("OK")
    logger.debug("NOK")

    my_filter.level = "DEBUG"
    logger.debug("OK")


Sending and receiving log messages across network or processes
--------------------------------------------------------------

It is possible to transmit logs between different processes and even between different computer if needed. Once the connection is established between the two Python programs, this requires serializing the logging record in one side while re-constructing the message on the other hand.

This can be achieved using a custom sink for the client and |patch| for the server.

.. code::

    # client.py
    import sys
    import socket
    import struct
    import time
    import pickle

    from loguru import logger


    class SocketHandler:

        def __init__(self, host, port):
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))

        def write(self, message):
            record = message.record
            data = pickle.dumps(record)
            slen = struct.pack(">L", len(data))
            self.sock.send(slen + data)

    logger.configure(handlers=[{"sink": SocketHandler('localhost', 9999)}])

    while 1:
        time.sleep(1)
        logger.info("Sending message from the client")


.. code::

    # server.py
    import socketserver
    import pickle
    import struct

    from loguru import logger


    class LoggingStreamHandler(socketserver.StreamRequestHandler):

        def handle(self):
            while True:
                chunk = self.connection.recv(4)
                if len(chunk) < 4:
                    break
                slen = struct.unpack('>L', chunk)[0]
                chunk = self.connection.recv(slen)
                while len(chunk) < slen:
                    chunk = chunk + self.connection.recv(slen - len(chunk))
                record = pickle.loads(chunk)
                level, message = record["level"].no, record["message"]
                logger.patch(lambda record: record.update(record)).log(level, message)

    server = socketserver.TCPServer(('localhost', 9999), LoggingStreamHandler)
    server.serve_forever()


Keep in mind though that `pickling is unsafe <https://intoli.com/blog/dangerous-pickles/>`_, use this with care.

Another possibility is to use a third party library like |zmq|_ for example.

.. code::

    # client.py
    import zmq
    from zmq.log.handlers import PUBHandler
    from loguru import logger

    socket = zmq.Context().socket(zmq.PUB)
    socket.connect("tcp://127.0.0.1:12345")
    handler = PUBHandler(socket)
    logger.add(handler)

    logger.info("Logging from client")


.. code::

    # server.py
    import sys
    import zmq
    from loguru import logger

    socket = zmq.Context().socket(zmq.SUB)
    socket.bind("tcp://127.0.0.1:12345")
    socket.subscribe("")

    logger.configure(handlers=[{"sink": sys.stderr, "format": "{message}"}])

    while True:
        _, message = socket.recv_multipart()
        logger.info(message.decode("utf8").strip())



Resolving ``UnicodeEncodeError`` and other encoding issues
----------------------------------------------------------

When you write a log message, the handler may need to encode the received `unicode`_ string to a specific sequence of bytes. The ``encoding`` used to perform this operation varies depending on the sink type and your environment. Problem may occur if you try to write a character which is not supported by the handler ``encoding``. In such case, it's likely that Python will raise an |UnicodeEncodeError|.

For example, this may happen while printing to the terminal::

    print("天")
    # UnicodeEncodeError: 'charmap' codec can't encode character '\u5929' in position 0: character maps to <undefined>

A similar error may occur while writing to a file which has not been opened using an appropriate encoding. Most common problem happen while logging to standard output or to a file on Windows. So, how to avoid such error? Simply by properly configuring your handler so that it can process any kind of unicode string.

If you are encountering this error while logging to ``stdout``, you have several options:

* Use |sys.stderr| instead of |sys.stdout| (the former will escape faulty characters rather than raising exception)
* Set the :envvar:`PYTHONIOENCODING` environment variable to ``utf-8``
* Call |sys.stdout.reconfigure| with ``encoding='utf-8'`` and / or ``errors='backslashreplace'``

If you are using a file sink, you can configure the ``errors`` or ``encoding`` parameter while adding the handler like ``logger.add("file.log", encoding="utf8")`` for example.  All additional ``**kwargs`` argument are passed to the built-in |open| function.

For other types of handlers, you have to check if there is a way to parametrize encoding or fallback policy.


Logging entry and exit of functions with a decorator
----------------------------------------------------

In some cases, it might be useful to log entry and exit values of a function. Although Loguru doesn't provide such feature out of the box, it can be easily implemented by using Python decorators::

    import functools
    from loguru import logger


    def logger_wraps(*, entry=True, exit=True, level="DEBUG"):

        def wrapper(func):
            name = func.__name__

            @functools.wraps(func)
            def wrapped(*args, **kwargs):
                logger_ = logger.opt(depth=1)
                if entry:
                    logger_.log(level, "Entering '{}' (args={}, kwargs={})", name, args, kwargs)
                result = func(*args, **kwargs)
                if exit:
                    logger_.log(level, "Exiting '{}' (result={})", name, result)
                return result

            return wrapped

        return wrapper

You could then use it like this::

    @logger_wraps()
    def foo(a, b, c):
        logger.info("Inside the function")
        return a * b * c

    def bar():
        foo(2, 4, c=8)

    bar()


Which would result in::

    2019-04-07 11:08:44.198 | DEBUG    | __main__:bar:30 - Entering 'foo' (args=(2, 4), kwargs={'c': 8})
    2019-04-07 11:08:44.198 | INFO     | __main__:foo:26 - Inside the function
    2019-04-07 11:08:44.198 | DEBUG    | __main__:bar:30 - Exiting 'foo' (result=64)


Here is another simple example to record timing of a function::

    def timeit(func):

        def wrapped(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            end = time.time()
            logger.debug("Function '{}' executed in {:f} s", func.__name__, end - start)
            return result

        return wrapped


Using logging function based on custom added levels
---------------------------------------------------

After adding a new level, it's habitually used with the |log| function::

    logger.level("foobar", no=33, icon="🤖", color="<blue>")

    logger.log("foobar", "A message")


For convenience, one can assign a new logging function which automatically uses the custom added level::

    from functools import partialmethod

    logger.__class__.foobar = partialmethod(logger.__class__.log, "foobar")

    logger.foobar("A message")


The new method need to be added only once and will be usable across all your files importing the ``logger``. Assigning the method to ``logger.__class__`` rather than ``logger`` directly ensures that it stays available even after calling ``logger.bind()``, ``logger.patch()`` and ``logger.opt()`` (because these functions return a new ``logger`` instance).


Preserving an ``opt()`` parameter for the whole module
------------------------------------------------------

Supposing you wish to color each of your log messages without having to call ``logger.opt(colors=True)`` every time, you can add this at the very beginning of your module::

    logger = logger.opt(colors=True)

    logger.info("It <green>works</>!")

However, it should be noted that it's not possible to chain |opt| calls, using this method again will reset the ``colors`` option to its default value (which is ``False``). For this reason, it is also necessary to patch the |opt| method so that all subsequent calls continue to use the desired value::

    from functools import partial

    logger = logger.opt(colors=True)
    logger.opt = partial(logger.opt, colors=True)

    logger.opt(raw=True).info("It <green>still</> works!\n")


Serializing log messages using a custom function
------------------------------------------------

Each handler added with ``serialize=True`` will create messages by converting the logging record to a valid JSON string. Depending on the sink for which the messages are intended, it may be useful to make changes to the generated string. Instead of using the ``serialize`` parameter, you can implement your own serialization function and use it directly in your sink::

    def serialize(record):
        subset = {"timestamp": record["time"].timestamp(), "message": record["message"]}
        return json.dumps(subset)

    def sink(message):
        serialized = serialize(message.record)
        print(serialized)

    logger.add(sink)


If you need to send structured logs to a file (or any kind of sink in general), a similar result can be obtained by using a custom ``format`` function::

    def formatter(record):
        # Note this function returns the string to be formatted, not the actual message to be logged
        record["extra"]["serialized"] = serialize(record)
        return "{extra[serialized]}\n"

    logger.add("file.log", format=formatter)


You can also use |patch| for this, so the serialization function will be called only once in case you want to use it in multiple sinks::

    def patching(record):
        record["extra"]["serialized"] = serialize(record)

    logger = logger.patch(patching)

    # Note that if "format" is not a function, possible exception will be appended to the message
    logger.add(sys.stderr, format="{extra[serialized]}")
    logger.add("file.log", format="{extra[serialized]}")


Rotating log file based on both size and time
---------------------------------------------

The ``rotation`` argument of file sinks accept size or time limits but not both for simplification reasons. However, it is possible to create a custom function to support more advanced scenarios::

    import datetime

    class Rotator:

        def __init__(self, *, size, at):
            now = datetime.datetime.now()

            self._size_limit = size
            self._time_limit = now.replace(hour=at.hour, minute=at.minute, second=at.second)

            if now >= self._time_limit:
                # The current time is already past the target time so it would rotate already.
                # Add one day to prevent an immediate rotation.
                self._time_limit += datetime.timedelta(days=1)

        def should_rotate(self, message, file):
            file.seek(0, 2)
            if file.tell() + len(message) > self._size_limit:
                return True
            if message.record["time"].timestamp() > self._time_limit.timestamp():
                self._time_limit += datetime.timedelta(days=1)
                return True
            return False

    # Rotate file if over 500 MB or at midnight every day
    rotator = Rotator(size=5e+8, at=datetime.time(0, 0, 0))
    logger.add("file.log", rotation=rotator.should_rotate)


Adapting colors and format of logged messages dynamically
---------------------------------------------------------

It is possible to customize the colors of your logs thanks to several :ref:`markup tags <color>`. Those are used to configure the ``format`` of your handler. By creating a appropriate formatting function, you can easily define colors depending on the logged message.

For example, if you want to associate each module with a unique color::

    from collections import defaultdict
    from random import choice

    colors = ["blue", "cyan", "green", "magenta", "red", "yellow"]
    color_per_module = defaultdict(lambda: choice(colors))

    def formatter(record):
        color_tag = color_per_module[record["name"]]
        return "<" + color_tag + ">[{name}]</> <bold>{message}</>\n{exception}"

    logger.add(sys.stderr, format=formatter)


If you need to dynamically colorize the ``record["message"]``, make sure that the color tags appear in the returned format instead of modifying the message::

    def rainbow(text):
        colors = ["red", "yellow", "green", "cyan", "blue", "magenta"]
        chars = ("<{}>{}</>".format(colors[i % len(colors)], c) for i, c in enumerate(text))
        return "".join(chars)

    def formatter(record):
        rainbow_message = rainbow(record["message"])
        # Prevent '{}' in message (if any) to be incorrectly parsed during formatting
        escaped = rainbow_message.replace("{", "{{").replace("}", "}}")
        return "<b>{time}</> " + escaped + "\n{exception}"

    logger.add(sys.stderr, format=formatter)


Dynamically formatting messages to properly align values with padding
---------------------------------------------------------------------

The default formatter is unable to vertically align log messages because the length of ``{name}``, ``{function}`` and ``{line}`` are not fixed.

One workaround consists of using padding with some maximum value that should suffice most of the time, like this for example::

    fmt = "{time} | {level: <8} | {name: ^15} | {function: ^15} | {line: >3} | {message}"
    logger.add(sys.stderr, format=fmt)

Others solutions are possible by using a formatting function or class. For example, it is possible to dynamically adjust the padding length based on previously encountered values::

    class Formatter:

        def __init__(self):
            self.padding = 0
            self.fmt = "{time} | {level: <8} | {name}:{function}:{line}{extra[padding]} | {message}\n{exception}"

        def format(self, record):
            length = len("{name}:{function}:{line}".format(**record))
            self.padding = max(self.padding, length)
            record["extra"]["padding"] = " " * (self.padding - length)
            return self.fmt

    formatter = Formatter()

    logger.remove()
    logger.add(sys.stderr, format=formatter.format)


Customizing the formatting of exceptions
----------------------------------------

Loguru will automatically add the traceback of occurring exception while using ``logger.exception()`` or ``logger.opt(exception=True)``::

    def inverse(x):
        try:
            1 / x
        except ZeroDivisionError:
            logger.exception("Oups...")

    if __name__ == "__main__":
        inverse(0)

.. code-block:: none

    2019-11-15 10:01:13.703 | ERROR    | __main__:inverse:8 - Oups...
    Traceback (most recent call last):
    File "foo.py", line 6, in inverse
        1 / x
    ZeroDivisionError: division by zero

If the handler is added with ``backtrace=True``, the traceback is extended to see where the exception came from:

.. code-block:: none

    2019-11-15 10:11:32.829 | ERROR    | __main__:inverse:8 - Oups...
    Traceback (most recent call last):
      File "foo.py", line 16, in <module>
        inverse(0)
    > File "foo.py", line 6, in inverse
        1 / x
    ZeroDivisionError: division by zero

If the handler is added with ``diagnose=True``, then the traceback is annotated to see what caused the problem:

.. code-block:: none

    Traceback (most recent call last):

    File "foo.py", line 6, in inverse
        1 / x
            └ 0

    ZeroDivisionError: division by zero

It is possible to further personalize the formatting of exception by adding an handler with a custom ``format`` function. For example, supposing you want to format errors using the |stackprinter|_ library::

    import stackprinter

    def format(record):
        format_ = "{time} {message}\n"

        if record["exception"] is not None:
            record["extra"]["stack"] = stackprinter.format(record["exception"])
            format_ += "{extra[stack]}\n"

        return format_

    logger.add(sys.stderr, format=format)

.. code-block:: none

    2019-11-15T10:46:18.059964+0100 Oups...
    File foo.py, line 17, in inverse
        15   def inverse(x):
        16       try:
    --> 17           1 / x
        18       except ZeroDivisionError:
        ..................................................
        x = 0
        ..................................................

    ZeroDivisionError: division by zero


Displaying a stacktrace without using the error context
-------------------------------------------------------

It may be useful in some cases to display the traceback at the time your message is logged, while no exceptions have been raised. Although this feature is not built-in into Loguru as it is more related to debugging than logging, it is possible to |patch| your logger and then display the stacktrace as needed (using the |traceback| module)::

    import traceback

    def add_traceback(record):
        extra = record["extra"]
        if extra.get("with_traceback", False):
            extra["traceback"] = "\n" + "".join(traceback.format_stack())
        else:
            extra["traceback"] = ""

    logger = logger.patch(add_traceback)
    logger.add(sys.stderr, format="{time} - {message}{extra[traceback]}")

    logger.info("No traceback")
    logger.bind(with_traceback=True).info("With traceback")

Here is another example that demonstrates how to prefix the logged message with the full call stack::

    import traceback
    from itertools import takewhile

    def tracing_formatter(record):
        # Filter out frames coming from Loguru internals
        frames = takewhile(lambda f: "/loguru/" not in f.filename, traceback.extract_stack())
        stack = " > ".join("{}:{}:{}".format(f.filename, f.name, f.lineno) for f in frames)
        record["extra"]["stack"] = stack
        return "{level} | {extra[stack]} - {message}\n{exception}"

    def foo():
        logger.info("Deep call")

    def bar():
        foo()

    logger.remove()
    logger.add(sys.stderr, format=tracing_formatter)

    bar()
    # Output: "INFO | script.py:<module>:23 > script.py:bar:18 > script.py:foo:15 - Deep call"


Manipulating newline terminator to write multiple logs on the same line
-----------------------------------------------------------------------

You can temporarily log a message on a continuous line by combining the use of |bind|, |opt| and a custom ``format`` function. This is especially useful if you want to illustrate a step-by-step process in progress, for example::

    def formatter(record):
        end = record["extra"].get("end", "\n")
        return "[{time}] {message}" + end + "{exception}"

    logger.add(sys.stderr, format=formatter)
    logger.add("foo.log", mode="w")

    logger.bind(end="").debug("Progress: ")

    for _ in range(5):
        logger.opt(raw=True).debug(".")

    logger.opt(raw=True).debug("\n")

    logger.info("Done")

.. code-block:: none

    [2020-03-26T22:47:01.708016+0100] Progress: .....
    [2020-03-26T22:47:01.709031+0100] Done

Note, however, that you may encounter difficulties depending on the sinks you use. Logging is not always appropriate for this type of end-user message.


Capturing standard ``stdout``, ``stderr`` and ``warnings``
----------------------------------------------------------

The use of logging should be privileged over |print|, yet, it may happen that you don't have plain control over code executed in your application. If you wish to capture standard output, you can suppress |sys.stdout| (and |sys.stderr|) with a custom stream object using |contextlib.redirect_stdout|. You have to take care of first removing the default handler, and not adding a new stdout sink once redirected or that would cause dead lock (you may use |sys.__stdout__| instead)::

    import contextlib
    import sys
    from loguru import logger

    class StreamToLogger:

        def __init__(self, level="INFO"):
            self._level = level

        def write(self, buffer):
            for line in buffer.rstrip().splitlines():
                logger.opt(depth=1).log(self._level, line.rstrip())

        def flush(self):
            pass

    logger.remove()
    logger.add(sys.__stdout__)

    stream = StreamToLogger()
    with contextlib.redirect_stdout(stream):
        print("Standard output is sent to added handlers.")


You may also capture warnings emitted by your application by replacing |warnings.showwarning|::

    import warnings
    from loguru import logger

    showwarning_ = warnings.showwarning

    def showwarning(message, *args, **kwargs):
        logger.warning(message)
        showwarning_(message, *args, **kwargs)

    warnings.showwarning = showwarning


Alternatively, if you want to emit warnings based on logged messages, you can simply use |warnings.warn| as a sink::


    logger.add(warnings.warn, format="{message}", filter=lambda record: record["level"].name == "WARNING")


Circumventing modules whose ``__name__`` value is absent
--------------------------------------------------------

Loguru makes use of the global variable ``__name__`` to determine from where the logged message is coming from. However, it may happen in very specific situation (like some Dask distributed environment) that this value is not set. In such case, Loguru will use ``None`` to make up for the lack of the value. This implies that if you want to |disable| messages coming from such special module, you have to explicitly call ``logger.disable(None)``.

Similar considerations should be taken into account while dealing with the ``filter`` attribute. As ``__name__`` is missing, Loguru will assign the ``None`` value to the ``record["name"]`` entry. It also means that once formatted in your log messages, the ``{name}`` token will be equals to ``"None"``. This can be worked around by manually overriding the ``record["name"]`` value using |patch| from inside the faulty module::

    # If Loguru fails to retrieve the proper "name" value, assign it manually
    logger = logger.patch(lambda record: record.update(name="my_module"))

You probably should not worry about all of this except if you noticed that your code is subject to this behavior.


Interoperability with ``tqdm`` iterations
-----------------------------------------

Trying to use the Loguru's ``logger`` during an iteration wrapped by the ``tqdm`` library may disturb the displayed progress bar. As a workaround, one can use the ``tqdm.write()`` function instead of writings logs directly to ``sys.stderr``::

    import time

    from loguru import logger
    from tqdm import tqdm

    logger.remove()
    logger.add(lambda msg: tqdm.write(msg, end=""), colorize=True)

    logger.info("Initializing")

    for x in tqdm(range(100)):
        logger.info("Iterating #{}", x)
        time.sleep(0.1)


You may encounter problems with colorization of your logs after importing ``tqdm`` using Spyder on Windows. This issue is discussed in `GH#132`_. You can easily circumvent the problem by calling ``colorama.deinit()`` right after your import.


Using Loguru's ``logger`` within a Cython module
------------------------------------------------

Loguru and Cython do not interoperate very well. This is because Loguru (and logging generally) heavily relies on Python stack frames while Cython, being an alternative Python implementation, try to get rid of these frames for optimization reasons.

Calling the ``logger`` from code compiled with Cython may raise this kind of exception::

    ValueError: call stack is not deep enough

This error happens when Loguru tries to access a stack frame which has been suppressed by Cython. There is no way for Loguru to retrieve contextual information of the logged message, but there exists a workaround that will at least prevent your application to crash::

    # Add this at the start of your file
    logger = logger.opt(depth=-1)

Note that logged messages should be displayed correctly, but function name and other information will be incorrect. This issue is discussed in `GH#88`_.


Creating independent loggers with separate set of handlers
----------------------------------------------------------

Loguru is fundamentally designed to be usable with exactly one global ``logger`` object dispatching logging messages to the configured handlers. In some circumstances, it may be useful to have specific messages logged to specific handlers.

For example, supposing you want to split your logs in two files based on an arbitrary identifier, you can achieve that by combining |bind| and ``filter``::

    from loguru import logger

    def task_A():
        logger_a = logger.bind(task="A")
        logger_a.info("Starting task A")
        do_something()
        logger_a.success("End of task A")

    def task_B():
        logger_b = logger.bind(task="B")
        logger_b.info("Starting task B")
        do_something_else()
        logger_b.success("End of task B")

    logger.add("file_A.log", filter=lambda record: record["extra"]["task"] == "A")
    logger.add("file_B.log", filter=lambda record: record["extra"]["task"] == "B")

    task_A()
    task_B()

That way, ``"file_A.log"`` and ``"file_B.log"`` will only contains logs from respectively the ``task_A()`` and ``task_B()`` function.

Now, supposing that you have a lot of these tasks. It may be a bit cumbersome to configure every handlers like this. Most importantly, it may unnecessarily slow down your application as each log will need to be checked by the ``filter`` function of each handler. In such case, it is recommended to rely on the |copy.deepcopy| built-in method that will create an independent ``logger`` object. If you add a handler to a deep copied ``logger``, it will not be shared with others functions using the original ``logger``::

    import copy
    from loguru import logger

    def task(task_id, logger):
        logger.info("Starting task {}", task_id)
        do_something(task_id)
        logger.success("End of task {}", task_id)

    logger.remove()

    for task_id in ["A", "B", "C", "D", "E"]:
        logger_ = copy.deepcopy(logger)
        logger_.add("file_%s.log" % task_id)
        task(task_id, logger_)

Note that you may encounter errors if you try to copy a ``logger`` to which non-picklable handlers have been added. For this reason, it is generally advised to remove all handlers before calling ``copy.deepcopy(logger)``.


Compatibility with ``multiprocessing`` using ``enqueue`` argument
-----------------------------------------------------------------

On Linux, thanks to |os.fork| there is no pitfall while using the ``logger`` inside another process started by the |multiprocessing| module. The child process will automatically inherit added handlers, the ``enqueue=True`` parameter is optional but is recommended as it would avoid concurrent access of your sink::

    # Linux implementation
    import multiprocessing
    from loguru import logger

    def my_process():
        logger.info("Executing function in child process")
        logger.complete()

    if __name__ == "__main__":
        logger.add("file.log", enqueue=True)

        process = multiprocessing.Process(target=my_process)
        process.start()
        process.join()

        logger.info("Done")

Things get a little more complicated on Windows. Indeed, this operating system does not support forking, so Python has to use an alternative method to create sub-processes called "spawning". This procedure requires the whole file where the child process is created to be reloaded from scratch. This does not interoperate very well with Loguru, causing handlers to be added twice without any synchronization or, on the contrary, not being added at all (depending on ``add()`` and ``remove()`` being called inside or outside the ``__main__`` branch). For this reason, the ``logger`` object need to be explicitly passed as an initializer argument of your child process::

    # Windows implementation
    import multiprocessing
    from loguru import logger

    def my_process(logger_):
        logger_.info("Executing function in child process")
        logger_.complete()

    if __name__ == "__main__":
        logger.remove()  # Default "sys.stderr" sink is not picklable
        logger.add("file.log", enqueue=True)

        process = multiprocessing.Process(target=my_process, args=(logger, ))
        process.start()
        process.join()

        logger.info("Done")

Windows requires the added sinks to be picklable or otherwise will raise an error while creating the child process. Many stream objects like standard output and file descriptors are not picklable. In such case, the ``enqueue=True`` argument is required as it will allow the child process to only inherit the queue object where logs are sent.

The |multiprocessing| library is also commonly used to start a pool of workers using for example |Pool.map| or |Pool.apply|. Again, it will work flawlessly on Linux, but it will require some tinkering on Windows. You will probably not be able to pass the ``logger`` as an argument for your worker functions because it needs to be picklable, but although handlers added using ``enqueue=True`` are "inheritable", they are not "picklable". Instead, you will need to make use of the ``initializer`` and ``initargs`` parameters while creating the |Pool| object in a way allowing your workers to access the shared ``logger``. You can either assign it to a class attribute or override the global logger of your child processes:

.. code::

    # workers_a.py
    class Worker:

        _logger = None

        @staticmethod
        def set_logger(logger_):
            Worker._logger = logger_

        def work(self, x):
            self._logger.info("Square rooting {}", x)
            return x**0.5


.. code::

    # workers_b.py
    from loguru import logger

    def set_logger(logger_):
        global logger
        logger = logger_

    def work(x):
        logger.info("Square rooting {}", x)
        return x**0.5


.. code::

    # main.py
    from multiprocessing import Pool
    from loguru import logger
    import workers_a
    import workers_b

    if __name__ == "__main__":
        logger.remove()
        logger.add("file.log", enqueue=True)

        worker = workers_a.Worker()
        with Pool(4, initializer=worker.set_logger, initargs=(logger, )) as pool:
            results = pool.map(worker.work, [1, 10, 100])

        with Pool(4, initializer=workers_b.set_logger, initargs=(logger, )) as pool:
            results = pool.map(workers_b.work, [1, 10, 100])

        logger.info("Done")

Independently of the operating system, note that the process in which a handler is added with ``enqueue=True`` is in charge of the queue internally used. This means that you should avoid to ``.remove()`` such handler from the parent process is any child is likely to continue using it. More importantly, note that a |Thread| is started internally to consume the queue. Therefore, it is recommended to call |complete| before leaving |Process| to make sure the queue is left in a stable state.
