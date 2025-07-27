Code Snippets and Recipes for Loguru
====================================

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
.. |os.umask| replace:: :func:`os.umask`
.. |multiprocessing| replace:: :mod:`multiprocessing`
.. |pickle| replace:: :mod:`pickle`
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

.. |if-name-equals-main| replace:: ``if __name__ == "__main__":``
.. _if-name-equals-main: https://docs.python.org/3/library/__main__.html#idiomatic-usage

.. |logot| replace:: ``logot``
.. _logot: https://logot.readthedocs.io/

.. |pytest| replace:: ``pytest``
.. _pytest: https://docs.pytest.org/en/latest/

.. |stackprinter| replace:: ``stackprinter``
.. _stackprinter: https://github.com/cknd/stackprinter

.. |zmq| replace:: ``zmq``
.. _zmq: https://github.com/zeromq/pyzmq

.. _`GH#132`: https://github.com/Delgan/loguru/issues/132


Security considerations when using Loguru
-----------------------------------------

Firstly, if you use |pickle| to load log messages (e.g. from the network), make sure the source is trustable or sign the data to verify its authenticity before deserializing it. If you do not take these precautions, malicious code could be executed by an attacker. You can read more details in this article: `What’s so dangerous about pickles? <https://intoli.com/blog/dangerous-pickles/>`_

.. code::

    import hashlib
    import hmac
    import pickle

    def client(connection):
        data = pickle.dumps("Log message")
        digest =  hmac.digest(b"secret-shared-key", data, hashlib.sha1)
        connection.send(digest + b" " + data)

    def server(connection):
        expected_digest, data = connection.read().split(b" ", 1)
        data_digest = hmac.digest(b"secret-shared-key", data, hashlib.sha1)
        if not hmac.compare_digest(data_digest, expected_digest):
            print("Integrity error")
        else:
            message = pickle.loads(data)
            logger.info(message)


You should also avoid logging a message that could be maliciously hand-crafted by an attacker. Calling ``logger.debug(message, value)`` is roughly equivalent to calling ``print(message.format(value))`` and the same safety rules apply. In particular, an attacker could force printing of assumed hidden variables of your application. Here is an article explaining the possible vulnerability: `Be Careful with Python's New-Style String Format <https://lucumr.pocoo.org/2016/12/29/careful-with-str-format/>`_.

.. code::

    SECRET_KEY = 'Y0UC4NTS33Th1S!'

    class SomeValue:
        def __init__(self, value):
            self.value = value

    # If user types "{value.__init__.__globals__[SECRET_KEY]}" then the secret key is displayed.
    message = "[Custom message] " + input()
    logger.info(message, value=SomeValue(10))


Another danger due to external input is the possibility of a log injection attack. Consider that you may need to escape user values before logging them: `Is your Python code vulnerable to log injection? <https://dev.arie.bovenberg.net/blog/is-your-python-code-vulnerable-to-log-injection/>`_

.. code::

    logger.add("file.log", format="{level} {message}")

    # If value is "Josh logged in.\nINFO User James" then there will appear to be two log entries.
    username = external_data()
    logger.info("User " + username + " logged in.")


Note that by default, Loguru will display the value of existing variables when an ``Exception`` is logged. This is very useful for debugging but could lead to credentials appearing in log files. Make sure to turn it off in production (or set the ``LOGURU_DIAGNOSE=NO`` environment variable).

.. code::

    logger.add("out.log", diagnose=False)


Another thing you should consider is to change the access permissions of your log file. Loguru creates files using the built-in |open| function, which means by default they might be read by a different user than the owner. If this is not desirable, be sure to modify the default access rights.

.. code::

    def opener(file, flags):
        return os.open(file, flags, 0o600)

    logger.add("combined.log", opener=opener)


Avoiding logs to be printed twice on the terminal
-------------------------------------------------

The logger is pre-configured for convenience with a default handler which writes messages to |sys.stderr|. You should |remove| it first if you plan to |add| another handler logging messages to the console, otherwise you may end up with duplicated logs.

.. code::

    logger.remove()  # Remove all handlers added so far, including the default one.
    logger.add(sys.stderr, level="WARNING")


.. _changing-level-of-existing-handler:

Changing the level of an existing handler
-----------------------------------------

Once a handler has been added, it is actually not possible to update it. This is a deliberate choice in order to keep the Loguru's API minimal. Several solutions are possible, though, if you need to change the configured ``level`` of a handler. Chose the one that best fits your use case.

The most straightforward workaround is to |remove| your handler and then re-|add| it with the updated ``level`` parameter. To do so, you have to keep a reference to the identifier number returned while adding a handler::

    handler_id = logger.add(sys.stderr, level="WARNING")

    logger.info("Logging 'WARNING' or higher messages only")

    ...

    logger.remove(handler_id)  # For the default handler, it's actually '0'.
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

    min_level = logger.level("DEBUG").no

    def filter_by_level(record):
        return record["level"].no >= min_level


    logger.remove()
    logger.add(sys.stderr, filter=filter_by_level, level=0)

    logger.debug("Logged")

    min_level = logger.level("WARNING").no

    logger.debug("Not logged")


.. _configuring-loguru-as-lib-or-app:

Configuring Loguru to be used by a library or an application
------------------------------------------------------------

A clear distinction must be made between the use of Loguru within a library or an application.

In case of an application, you can add handlers from anywhere in your code. It's advised though to configure the logger from within a |if-name-equals-main|_ block inside the entry file of your script.

However, if your work is intended to be used as a library, you usually should not add any handler. This is user responsibility to configure logging according to its preferences, and it's better not to interfere with that. Indeed, since Loguru is based on a single common logger, handlers added by a library will also receive user logs, which is generally not desirable.

By default, a third-library should not emit logs except if specifically requested. For this reason, there exist the |disable| and |enable| methods. Make sure to first call ``logger.disable("mylib")``. This avoids library logs to be mixed with those of the user. The user can always call ``logger.enable("mylib")`` if he wants to access the logs of your library.

If you would like to ease logging configuration for your library users, it is advised to provide a function like ``configure_logger()`` in charge of adding the desired handlers. This will allow the user to activate the logging only if he needs to.

To summarize, let's look at this hypothetical package (none of the listed files are required, it all depends on how you plan your project to be used):

.. code:: text

    mypackage
    ├── __init__.py
    ├── __main__.py
    ├── main.py
    └── mymodule.py

Files relate to Loguru as follows:

* File ``__init__.py``:

    * It is the entry point when your project is used as a library (``import mypackage``).
    * It should contain ``logger.disable("mypackage")`` unconditionally at the top level.
    * It should not call ``logger.add()`` as it modifies handlers configuration.

* File ``__main__.py``:

    * It is the entry point when your project is used as an application (``python -m mypackage``).
    * It can contain logging configuration unconditionally at the top level.

* File ``main.py``:

    * It is the entry point when your project is used as a script (``python mypackage/main.py``).
    * It can contain logging configuration inside an ``if __name__ == "__main__":`` block.

* File ``mymodule.py``:

    * It is an internal module used by your project.
    * It can use the ``logger`` simply by importing it.
    * It does not need to configure anything.


.. _inter-process-communication:

Transmitting log messages across network, processes or Gunicorn workers
-----------------------------------------------------------------------

It is possible to send and receive logs between different processes and even between different computers if needed. Once the connection is established between the two Python programs, this requires serializing the logging record in one side while re-constructing the message on the other hand. Keep in mind though that `pickling is unsafe <https://intoli.com/blog/dangerous-pickles/>`_, you should use this with care.

The first thing you will need is to run a server responsible for receiving log messages emitted by other processes::

    # server.py
    import socketserver
    import pickle
    import struct
    import sys
    from loguru import logger


    class LoggingRequestHandler(socketserver.StreamRequestHandler):

        def handle(self):
            while True:
                chunk = self.connection.recv(4)
                if len(chunk) < 4:
                    break
                slen = struct.unpack(">L", chunk)[0]
                chunk = self.connection.recv(slen)
                while len(chunk) < slen:
                    chunk = chunk + self.connection.recv(slen - len(chunk))
                record = pickle.loads(chunk)
                level, message = record["level"].name, record["message"]
                logger.patch(lambda r, record=record: r.update(record)).log(level, message)


    if __name__ == "__main__":
        # Configure the logger with desired handlers.
        logger.configure(handlers=[{"sink": "server.log"}, {"sink": sys.stderr}])

        # Setup the server to receive log messages from other processes.
        with socketserver.TCPServer(("localhost", 9999), LoggingRequestHandler) as server:
            server.serve_forever()


Then, you need your clients to send messages using a specific handler::

    # client.py
    import socket
    import struct
    import time
    import pickle
    from loguru import logger


    class SocketHandler:

        def __init__(self, host, port):
            self._host = host
            self._port = port

        def write(self, message):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self._host, self._port))
            record = message.record
            data = pickle.dumps(record)
            slen = struct.pack(">L", len(data))
            sock.send(slen + data)


    if __name__ == "__main__":
        # Setup the handler sending log messages to the server.
        logger.configure(handlers=[{"sink": SocketHandler('localhost', 9999)}])

        # Proceed with standard logger usage.
        logger.info("Sending message from the client")


Make sure that the server is running while the clients are logging messages, and note that they must communicate on the same port.

Another example, when using Gunicorn and FastAPI you should add the previously defined ``SocketHandler`` to each of the running workers, possibly like so::

    from contextlib import asynccontextmanager
    from fastapi import FastAPI
    from loguru import logger

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Setup the server instance (executed once for each worker)."""
        logger.configure(handlers=[{"sink": SocketHandler("localhost", 9999)}])
        logger.debug("Worker is initializing")
        yield

    app = FastAPI(lifespan=lifespan)

When sharing the logger between processes is not technically possible, using a server handling TCP requests is the most reliable way of guaranteeing the integrity of logged messages.


Using ZMQ to send and receive log messages
------------------------------------------

Third-party libraries like |zmq|_ can be leveraged to exchange messages between multiple processes. Here is an example of a basic server and client:

.. code::

    # client.py
    import zmq
    from zmq.log.handlers import PUBHandler
    from logging import Formatter
    from loguru import logger

    socket = zmq.Context().socket(zmq.PUB)
    socket.connect("tcp://127.0.0.1:12345")
    handler = PUBHandler(socket)
    handler.setFormatter(Formatter("%(message)s"))
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


Which would result in:

.. code-block:: none

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

Finally, here is an example of a generic wrapper that combines a success message with error handling during function execution::

    def with_logging(func):
        @functools.wraps(func)
        @logger.catch(message=f"Error in {func.__name__}")
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            logger.success(f"Successfully completed {func.__name__}")
            return result

        return wrapper

    @with_logging
    def may_fail(x):
        if x < 0:
            raise ValueError("Negative value!")
        return x * 2

    may_fail(10)  # Should log success
    may_fail(-5)  # Should log an error


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


Setting permissions on created log files
----------------------------------------

To set desired permissions on created log files, use the ``opener`` argument to pass in a custom opener with permissions octal::

    def opener(file, flags):
        return os.open(file, flags, 0o600)  # read/write by owner only

    logger.add("foo.log", rotation="100 kB", opener=opener)

When using an opener argument, all created log files including ones created during rotation will use the initially provided opener.

Note that the provided mode will be masked out by the OS `umask <https://en.wikipedia.org/wiki/Umask>`_ value (describing which bits are *not* to be set when creating a file or directory). This value is conventionally equals to ``0o022``, which means specifying a ``0o666`` mode will result in a ``0o666 - 0o022 = 0o644`` file permission in this case (which is actually the default). It is possible to change the umask value by first calling |os.umask|, but this needs to be done with careful consideration, as it changes the value globally and can cause security issues.


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

One workaround consists of using padding with some maximum value that should suffice most of the time. For this purpose, you can use Python's string formatting directives, like in this example::

    fmt = "{time} | {level: <8} | {name: ^15} | {function: ^15} | {line: >3} | {message}"
    logger.add(sys.stderr, format=fmt)

Here, ``<``, ``^`` and ``>`` will left, center, and right-align the respective keys, and pad them to a maximum length.

Other solutions are possible by using a formatting function or class. For example, it is possible to dynamically adjust the padding length based on previously encountered values::

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
        logger.opt(depth=2).warning(message)
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

Calling the ``logger`` from code compiled with Cython may result in "incomplete" logs (missing call context):

.. code-block:: none

    2024-11-26 15:58:48.985 | INFO     | None:<unknown>:0 - Message from Cython!

This happens when Loguru tries to access a stack frame which has been suppressed by Cython. In such a case, there is no way for Loguru to retrieve contextual information of the logged message.

You can update the default ``format`` of your handlers and omit the uninteresting fields. You can also tries to |patch| the ``logger`` to manually add information you may know about the caller, for example::

    logger = logger.patch(lambda record: record.update(name="my_cython_module"))

Note that the ``"name"`` attribute of the log record is set to ``None`` when the frame is unavailable.


.. _creating-independent-loggers:

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


.. _multiprocessing-compatibility:

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

Another thing to keep in mind when dealing with multiprocessing is the fact that handlers created with ``enqueue=True`` create a queue internally in the default multiprocessing context. If they are passed through to a subprocesses instantiated within a different context (e.g. with ``multiprocessing.get_context("spawn")`` on linux, where the default context is ``"fork"``) it will most likely result in crashing the subprocess. This is also noted in the `python multiprocessing docs <https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods>`_. To prevent any problems, you should specify the context to be used by Loguru while adding the handler. This can be done by passing the ``context`` argument to the ``add()`` method::

    import multiprocessing
    from loguru import logger
    import workers_a

    if __name__ == "__main__":
        context = multiprocessing.get_context("spawn")

        logger.remove()
        logger.add("file.log", enqueue=True, context=context)

        worker = workers_a.Worker()
        with context.Pool(4, initializer=worker.set_logger, initargs=(logger, )) as pool:
            results = pool.map(worker.work, [1, 10, 100])


.. _recipes-testing:

Unit testing logs emitted by Loguru
-----------------------------------

Logging calls can be tested using |logot|_, a high-level log testing library with built-in support for Loguru::

    from logot import Logot, logged

    def test_something(logot: Logot) -> None:
        do_something()
        logot.assert_logged(logged.info("Something was done"))

Enable Loguru log capture in your |pytest|_ configuration:

.. code:: toml

   [tool.pytest.ini_options]
   logot_capturer = "logot.loguru.LoguruCapturer"

.. seealso::

    See `using logot with Loguru <https://logot.readthedocs.io/latest/integrations/loguru.html>`_ for more information
    about `configuring pytest <https://logot.readthedocs.io/latest/integrations/loguru.html#enabling-for-pytest>`_
    and `configuring unittest <https://logot.readthedocs.io/latest/integrations/loguru.html#enabling-for-unittest>`_.

.. note::

    When migrating an existing project from standard :mod:`logging`, it can be useful to migrate your existing test
    cases too. See :ref:`migrating assertLogs() <migration-assert-logs>` and :ref:`migrating caplog <migration-caplog>`
    for more information.
