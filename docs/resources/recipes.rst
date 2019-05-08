Code snippets and recipes for ``loguru``
========================================

.. highlight:: python3

.. |print| replace:: :func:`print()`
.. |sys.__stdout__| replace:: :data:`sys.__stdout__`
.. |sys.stdout| replace:: :data:`sys.stdout`
.. |sys.stderr| replace:: :data:`sys.stderr`
.. |warnings| replace:: :mod:`warnings`
.. |warnings.showwarning| replace:: :func:`warnings.showwarning`

.. |add| replace:: :meth:`~loguru._logger.Logger.add()`
.. |remove| replace:: :meth:`~loguru._logger.Logger.remove()`
.. |bind| replace:: :meth:`~loguru._logger.Logger.bind`
.. |opt| replace:: :meth:`~loguru._logger.Logger.opt()`
.. |level| replace:: :meth:`~loguru._logger.Logger.level()`
.. |configure| replace:: :meth:`~loguru._logger.Logger.configure()`


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
