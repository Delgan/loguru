Code snippets and recipes for ``loguru``
========================================

.. highlight:: python3

.. |print| replace:: :func:`print()`
.. |sys.__stdout__| replace:: :data:`sys.__stdout__`
.. |sys.stdout| replace:: :data:`sys.stdout`
.. |sys.stderr| replace:: :data:`sys.stderr`
.. |warnings| replace:: :mod:`warnings`
.. |warnings.showwarning| replace:: :func:`warnings.showwarning`
.. |copy.deepcopy| replace:: :func:`copy.deepcopy`

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
                level, message = record["level"], record["message"]
                logger.patch(lambda record: record.update(record)).log(level, message)

    server = socketserver.TCPServer(('localhost', 9999), LoggingStreamHandler)
    server.serve_forever()


Keep in mind though that `pickling is unsafe <https://intoli.com/blog/dangerous-pickles/>`_, use this with care.


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

    def foobar(_, message, *args, **kwargs):
        logger.opt(depth=1).log("foobar", message, *args, **kwargs)

    logger.__class__.foobar = foobar

    logger.foobar("A message")


The new method need to be added only once and will be usable across all your files importing the ``logger``. Note that the call to ``opt(depth=1)`` is necessary to make sure that the logged message contains contextual information of the parent stack frame (where ``logger.foobar()`` is called). Also, assigning the method to ``logger.__class__`` rather than ``logger`` directly ensures that it stays available even after calling ``logger.bind()``, ``logger.patch()`` and ``logger.opt()`` (because these functions return a new ``logger`` instance).


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


Capturing standard ``stdout``, ``stderr`` and ``warnings``
----------------------------------------------------------

The use of logging should be privileged over |print|, yet, it may happen that you don't have plain control over code executed in your application. If you wish to capture standard output, you can suppress |sys.stdout| (and |sys.stderr|) with a custom stream object. You have to take care of first removing the default handler, and not adding a new stdout sink once redirected or that would cause dead lock (you may use |sys.__stdout__| instead)::

    import sys
    from loguru import logger


    class StreamToLogger:

        def __init__(self, level="INFO"):
            self._level = level

        def write(self, buffer):
            for line in buffer.rstrip().splitlines():
                logger.log(self._level, line.rstrip())

        def flush(self):
            pass

    logger.remove()
    logger.add(sys.__stdout__)

    sys.stdout = StreamToLogger()


You may also capture warnings emitted by your application by replacing |warnings.showwarning|::

    import warnings
    from loguru import logger

    showwarning_ = warnings.showwarning

    def showwarning(message, *args, **kwargs):
        logger.warning(message)
        showwarning_(message, *args, **kwargs)

    warnings.showwarning = showwarning


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
    logger.add(tqdm.write, end="")

    logger.info("Initializing")

    for x in tqdm(range(100)):
        logger.info("Iterating #{}", x)
        time.sleep(0.1)


You may encounter problems with colorization of your logs after importing ``tqdm`` using Spyder on Windows. This issue is discussed in `GH#132`_. You can easily circunvent the problem by calling ``colorama.deinit()`` right after your import.


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

Now, supposing that you have a lot of these tasks. It may be a little bit cumbersome to configure every handlers like this. Most importantly, it may unceserratily slow down your application as each logs will need to be checked by the ``filter`` function of each handler. In such case, it is recommanded to rely on the |copy.deepcopy| built-in method that will create an independant ``logger`` object. If you add a handler to a deepcopied ``logger``, it will not be shared with others functions using the original ``logger``::

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
