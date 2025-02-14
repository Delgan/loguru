Frequently Asked Questions and Troubleshooting Tips for Loguru
==============================================================

.. highlight:: python3

.. |sys.stdout| replace:: :data:`sys.stdout`
.. |sys.stderr| replace:: :data:`sys.stderr`
.. |str.format| replace:: :meth:`str.format()`
.. |isatty| replace:: :meth:`~io.IOBase.isatty`
.. |IOBase.close| replace:: :meth:`~io.IOBase.close`

.. |Logger| replace:: :class:`~loguru._logger.Logger`
.. |add| replace:: :meth:`~loguru._logger.Logger.add()`
.. |remove| replace:: :meth:`~loguru._logger.Logger.remove()`
.. |bind| replace:: :meth:`~loguru._logger.Logger.bind()`
.. |opt| replace:: :meth:`~loguru._logger.Logger.opt()`
.. |patch| replace:: :meth:`~loguru._logger.Logger.patch()`

.. |colorama| replace:: ``colorama``
.. _colorama: https://github.com/tartley/colorama

.. |if-name-equals-main| replace:: ``if __name__ == "__main__":``
.. _if-name-equals-main: https://docs.python.org/3/library/__main__.html#idiomatic-usage

.. |the-no-color-environment-variable| replace:: the ``NO_COLOR`` environment variable
.. _the-no-color-environment-variable: https://no-color.org/

.. _ANSI escape sequences: https://en.wikipedia.org/wiki/ANSI_escape_code


How do I create and configure a logger?
---------------------------------------

Loguru differs from standard logging as you don't need to create a logger. It is directly provided by Loguru, and you should just import it::

    from loguru import logger

    logger.info("Hello, World!")

This |Logger| object is unique and shared across all modules of your application. Import it into every file where you need to use it. It acts as a basic facade interface around a list of handlers. These handlers are responsible for receiving log messages, formatting them, and logging them to one or more desired destinations (file, console, etc.).

When you first import Loguru's logger, it comes pre-configured with a default handler that displays your logs on the standard error output (|sys.stderr|). However, you can easily change the logger's configuration to suit your needs. First, use |remove| to discard the default handler. Then, use |add| to register one or more handlers that will log messages to the desired destinations. For example::

    logger.remove()  # Remove the default handler.
    logger.add(sys.stderr, format="{time} - {level} - {message}")  # Log to console with custom format.
    logger.add("file.log", level="INFO", rotation="500 MB")  # Also log to a file, rotating every 500 MB.

The logger should be configured only once, at the entry point of your application (typically within a |if-name-equals-main|_ block). Other modules in your application will automatically inherit this configuration by simply importing Loguru's global ``logger``.

.. seealso::

   :ref:`Configuring Loguru to be used by a library or an application <configuring-loguru-as-lib-or-app>`


Why are my logs duplicated in the output?
-----------------------------------------

Remember that the initial ``logger`` has a default handler for convenience. If you plan to change the logging configuration, make sure to |remove| this default handler before to |add| a new one. Otherwise, messages will be duplicated because they will be sent to both the default handler and your new handler::

    # Replace the default handler with a new one.
    logger.remove()
    logger.add(sys.stderr, format="{time} - {level} - {message}")

Additionally, since there is a single ``logger`` shared across all modules in your application, you should configure it in one place only. Handlers will be added as many times as ``logger.add()`` is called, so be careful not to reconfigure it multiple times.

In particular when using ``multiprocessing`` (either directly or indirectly through a web framework, for instance), ensure that the ``logger`` configuration is guarded by an if |if-name-equals-main|_ block. Otherwise, each spawned child process will re-execute the configuration code. This can result in duplicated logs or unexpected configurations. See :ref:`this section of the documentation <multiprocessing-compatibility>` for details.

Finally, don't forget that the ``level`` argument of |add| defines a minimum threshold, not an exact filtering mechanism. It is generally a mistake to add two handlers with the same sink, as it will cause duplication unless they are configured with mutually exclusive ``filter`` functions. For example::

    def is_debug(record):
        return record["level"].no <= 10

    logger.add(sys.stderr, level="DEBUG", format="{time} - {name} - {message}", filter=is_debug)
    logger.add(sys.stderr, level="INFO", format="{message}", filter=lambda r: not is_debug(r))


How do I set the logging level?
-------------------------------

The :ref:`logging levels <levels>` allow filtering messages based on their importance. It is a minimum threshold above which messages are logged (or ignored otherwise). This makes it possible, for example, to adjust the verbosity of logs depending on the execution environment (development or production).

The |Logger| itself is not associated with any specific level. Instead, it is the level of each handler that individually determines whether a message is logged or not. This level is defined when configuring the handler and adding it to the logger using the ``level`` argument of the |add| method::

    logger.add(sys.stdout, level="WARNING")  # Log only messages with level "WARNING" or higher.
    logger.debug("Some debug message")  # Will be ignored.
    logger.error("Some error message")  # Will be displayed.

It is not possible to change the level of an existing handler. If you need to modify the logging level, you can |remove| the existing handler and |add| a new one with the desired level::

    logger.remove()  # Remove the default handler.
    logger.add(sys.stderr, level="INFO")

By default, the level of each handler is ``"DEBUG"``. You can adjust this value :ref:`using environment variables <env>`.

.. seealso::

   :ref:`Changing the level of an existing handler <changing-level-of-existing-handler>`


How do I customize the log format and re-use the default one?
-------------------------------------------------------------

The log format must be defined using the ``format`` argument of the |add| method::

    logger.add(sys.stderr, format="{time} - {level} - {message}")

Refer to :ref:`this section of the documentation <record>` to learn about the different formatting variables available. You can also use :ref:`color tags <color>`::

    logger.add(sys.stderr, format="<green>{time}</> - {level} - <lvl>{message}</>")

For advanced configuration, the ``format`` argument also accepts a function, allowing you to dynamically generate the desired format. Be aware that in this case, you have to explicitly include the line ending and exception field (since you gain full control over the formatting, while ``"\n{exception}"`` is added automatically when the ``format`` is a string). For example, to include the thread identifier but only for error messages and above::

        def custom_formatter(record):
            if record["level"].no >= 40:
                return "<green>{time}</> - {level} - <red>{thread}</> - <lvl>{message}</>\n{exception}"
            else:
                return "<green>{time}</> - {level} - <lvl>{message}</lvl>\n{exception}"

        logger.add(sys.stderr, format=custom_formatter)

Finally, note that accessing the default log format is not directly possible, as it would only be useful in a very limited number of cases. Instead, you need to explicitly redefine your desired format. To quickly copy-paste the default logging format, check out the ``LOGURU_FORMAT`` variable `in the source code <https://github.com/Delgan/loguru/blob/master/loguru/_defaults.py>`_.


Why are my logs not colored?
----------------------------

Log colors are configured using :ref:`special tags <color>` in the ``format`` of the handlers. If you use a custom ``format``, make sure that these tags are included, for example::

    logger.add(sys.stderr, format="<green>{time}</green> | <level>{message}</level>")

When adding a handler with ``colorize=None`` (the default), Loguru tries to automatically detect whether the added sink (such as ``sys.stderr`` in the above example) supports colors. If it's not the case, color tags will be stripped. Otherwise, they'll be converted to `ANSI escape sequences`_.

These sequences are generally only supported within a terminal. Therefore, it is normal that you don't see colors when logs are saved to a text file. Sinks that support colors are usually |sys.stderr| and |sys.stdout|::

    logger.add(sys.stderr)  # Can be colored.
    logger.add("file.log")  # Cannot be colored.

When such stream object is used for logging, Loguru will also call |isatty| to determine whether colors should be used. This method notably returns ``False`` if the stream is not connected to a terminal, which would make colorization pointless. For example, redirecting the output of your script to a file will disable colors:

.. code-block:: bash

    python my_script.py > output.log  # Colors will be disabled.

Additionally, it is not uncommon in some virtual environments for the standard output not to be considered as connected to a terminal, even though you can view the logs' output live without redirection. This is the case, for instance, in some cloud services. Check the value of ``sys.stderr.isatty()`` if you encounter any issues.

Various heuristics assist in determining whether colors should be enabled by default. Specifically, Loguru honors |the-no-color-environment-variable|_ and disables coloring if it is set to any value. Additionally, terminals identified by ``TERM=dumb`` are considered to lack color support.

In any case, you can always control log coloring by explicitly specifying the ``colorize`` argument of the |add| method::

    logger.add(sys.stderr, colorize=True)  # Force ANSI sequences in output.

Conversely, if raw ANSI sequences such as ``\x1b[31m`` or ``\x1b[0m`` appear in your logs, it certainly means the sink does not support colors, and you should disable them.

Note that on Windows, log coloring is handled using the |colorama|_ library.


Why are my logs not showing up?
-------------------------------

Ensure that you've added at least one sink using |add|. You can get an overview of the configured handlers by simply printing the logger object::

    print(logger)
    # Output: <loguru.logger handlers=[(id=0, level=10, sink=<stderr>)]>


Check also the logging level: messages below the set level won't appear::

    logger.add(sys.stderr, level="INFO")
    logger.debug("Some debug message")  # Won't be displayed since "DEBUG" is below "INFO".


Why is the captured exception missing from the formatted message?
-----------------------------------------------------------------

When ``logger.exception()`` or ``logger.opt(exception=True)`` is used within an ``except`` clause, Loguru automatically captures the exception information and includes it in :ref:`the logged message <message>`.

The position of the exception in the message is controlled by the ``"{exception}"`` field of the configured log format. By default, when the ``format`` argument of |add| is a string, the ``"{exception}"`` field is automatically appended to the format::

    # The "{exception}" placeholder is implicit here (at the end of the format).
    log_format = "{time} - {level} - {message}"
    logger.add(sys.stderr, format=log_format)


However, when using a custom function to define the format of logs, the user gets complete control over the desired format. This means the ``"{exception}"`` field must be explicitly included::

    def custom_formatter(record):
        return "{time} - {level} - {message}\n{exception}"

    logger.add(sys.stderr, format=custom_formatter)

If the field is missing, the formatted error will not appear in the log message. Always ensure the ``"{exception}"`` placeholder is present in your log format if you want exception details to appear in your logs.


How can I use different loggers in different modules of my application?
-----------------------------------------------------------------------

Since Loguru is designed on the use of a single ``logger``, it is fundamentally not possible to create different loggers for multiple modules. The idea is that modules should simply import the global ``logger`` from ``loguru``, and log differentiation should be handled through handlers (which should only be configured once, at the application's entry point).

Note that is generally possible to identify the origin of a log message via the ``record["name"]`` field in the record dict. This field contains the name of the module that emitted the message. For example, you can use this information to redirect messages based on their origin::

    logger.add("my_app.log")  # All messages.
    logger.add("module_1.log", filter="module_1")  # Messages from "module_1" only.
    logger.add("module_2.log", filter="module_2")  # Messages from "module_2" only.

For more advanced use cases, it is recommended to use the |bind| method, which returns a new instance of the ``logger`` tied to the given value. This allows you to identify logs more precisely::

    def is_specific_log(record):
        return record["extra"].get("is_specific") is True

    logger.add("specific.log", filter=is_specific_log)
    logger.add("other.log", filter=lambda r: not is_specific_log(r))

    specific_logger = logger.bind(is_specific=True)
    specific_logger.info("This message will go to 'specific.log' only.")

    logger.info("This message will go to 'other.log' only.")

.. seealso::

   :ref:`Creating independent loggers with separate set of handlers <creating-independent-loggers>`


Why are my log files sometimes duplicated or the content trimmed?
-----------------------------------------------------------------

Problem with logging files duplicated or trimmed is generally symptomatic of a configuration issue. More precisely, this can happen if |add| is inadvertently called multiple times with the same file path.

When this happens, the file is opened again by the newly created handler. Consequently, multiple handlers manage and write to the same file concurrently. This is an incorrect situation that inevitably leads to conflicts. If the problem isn't detected, handlers risk overwriting logs over each other, otherwise it can also result in duplicated files at the moment of the rotation.

If you observe such weird behavior, you should review your code carefully to ensure that the same file sink is not being added multiple times. This can occur if ``multiprocessing`` is used incorrectly (see :ref:`this section of the documentation <multiprocessing-compatibility>` for more details). You have to make sure that the logger is not configured repeatedly by different processes, and you should use a |if-name-equals-main|_ guard.

It is also a common issue with web frameworks like Gunicorn and Uvicorn, as they start multiple workers in parallel. In such cases, you need to set up a log server, and configure workers to send messages to it using a socket. Refer to :ref:`Transmitting log messages across network, processes or Gunicorn workers <inter-process-communication>` for details.


Why logging a message with f-string sometimes raises an exception?
------------------------------------------------------------------

When positional or keyword arguments are passed to the logging function, Loguru will integrate them to the message. For example::

    logger.info("My name is {name}", name="John")
    # Output: [INFO] My name is John

This is actually equivalent to using the |str.format| built-in Python method::

    message = "My name is {name}".format(name="John")
    logger.info(message)

However, the behavior described above can cause an error if the arguments passed were not intended to be formatted with the message (but rather just captured in the "extra" dict of the log record). This is particularly true if the message contains curly braces. The formatting function will then interpret them as placeholders and attempt to replace them with the passed arguments.

Here are some examples that result in various exceptions:

.. code-block::

    # KeyError: 'key1, key2'
    logger.warning("Config file missing keys: {key1, key2}", filename="app.cfg")

.. code-block::

    # ValueError: Single '{' encountered in format string
    logger.info("This is a curly bracket: {", foo="bar")

.. code-block::

    # AttributeError: 'dict' object has no attribute 'format'
    logger.debug({"key": "value"}, identifier=42)

.. code-block::

    # IndexError: Replacement index 0 out of range for positional args tuple
    logger.error("Use 'set()' not '{}' for empty set", strictness=9)


It is common to encounter these errors when using f-strings, as this can leads to the creation of a message that already contains curly braces. For example::

    data = {"foo": 42}

    # Will raise "KeyError" because it's equivalent to:
    #   logger.info("Processing '{'foo': 42}'", data=data)
    logger.info(f"Processing '{data}'", data=data)

Therefore, you must be careful not to inadvertently introduce curly braces into the message. Instead of using an f-string, you can let Loguru handle the formatting::

    logger.info("Processing '{data}'", data=data)

You can also use |bind| to add extra information to a message without formatting it::

    logger.bind(data=data).info(f"Processing '{data}'")

Finally, you can possibly disable formatting by doubling the curly braces::

    logger.info("Curly brackets are {{ and }}", data=data)


How do I fix "ValueError: I/O operation error on closed file"?
--------------------------------------------------------------

This error occurs because the logger is trying to write to a stream object (like ``sys.stderr`` or ``sys.stdout``) that has been closed, which is invalid (see |IOBase.close|).

When stream objects are used as logging sink, Loguru will not close them. This would be very inconvenient and incorrect (as the stream is global, it must remain usable after the sink has been removed). Since Loguru does not close such a stream by itself, this means something else closed the stream while it was still in use by the ``logger``.

This is generally due to some tools or specific environments that take the liberty of replacing ``sys.stdout`` and ``sys.stderr`` with their own stream object. In this way, they can capture what is written to the standard output. This is the case with some libraries, IDEs and cloud platforms.
The problem is that the ``logger`` will use this wrapped stream as well. If the third-party tool happens to clean up and close the stream, then the ``logger`` is left with an unusable sink.

Here is a simplified example to illustrate the issue::

    from contextlib import contextmanager
    import sys
    import io
    from loguru import logger


    @contextmanager
    def redirect_stdout(new_target):
        old_target, sys.stdout = sys.stdout, new_target
        try:
            yield new_target
        finally:
            sys.stdout = old_target
            new_target.close()


    if __name__ == "__main__":
        logger.remove()
        f = io.StringIO()

        with redirect_stdout(f):
            logger.add(sys.stdout)  # Logger is inadvertently configured with wrapped stream.
            logger.info("Hello")
            output = f.getvalue()

        print(f"Captured output: {output}")

        # ValueError: I/O operation on closed file.
        logger.info("World")


And here is another example causing the same error with Pytest::

    import sys
    from loguru import logger

    logger.remove()

    def test_1(capsys):
        # Here, "sys.stderr" is actually a mock object due to usage of "capsys" fixture.
        logger.add(sys.stderr, catch=False)
        logger.info("Test 1")


    def test_2():
        # After execution of the previous test, the mocked "sys.stderr" was closed by Pytest.
        # However, the handler was not removed from the Loguru logger. It'll raise a "ValueError" here.
        logger.info("Test 2", catch=False)


What you can possibly do in such a situation:

- identify any tool that could be manipulating ``sys.stdout``, try to call ``print(sys.stdout)`` to see if it's a wrapper object;
- make sure the ``logger`` is always fully re-initialized whenever your code is susceptible to clean up the wrapped ``sys.stdout``;
- configure the ``logger`` with ``logger.add(lambda m: sys.stdout.write(m))`` instead of ``logger.add(sys.stdout)``, so that the stream is dynamically retrieved and therefore not affected by changes.


How do I prevent "RuntimeError" due to "deadlock avoided"?
----------------------------------------------------------

The logging functions are not reentrant. This means you must not use the logger when it's already in use in the same thread. This situation can occur notably if you use the logger inside a sink (which itself is called by the logger). Logically, this would result in an infinite recursive loop. In practice, it would more likely cause your application to hang because logging is protected by an internal lock.

To prevent such problems, there is a mechanism that detects and prevents the logger from being called recursively. This is what might lead to a ``RuntimeError``. When faced with such an error, you need to ensure that the handlers you configure do not internally call the logger. This also applies to the logger from the standard ``logging`` library.

If you cannot prevent the use of the logger inside a handler, you should implement a ``filter`` to avoid recursive calls. For example::

    import sys
    from loguru import logger


    def my_sink(message):
        logger.debug("Within my sink")
        print(message, end="")


    def avoid_recursion(record):
        return record["function"] != "my_sink"


    if __name__ == "__main__":
        logger.remove()
        logger.add("file.log")
        logger.add(my_sink, filter=avoid_recursion)

        logger.info("First message")
        logger.debug("Another message")


Why is the source (name, file, function, line) of the log message incorrect or missing?
---------------------------------------------------------------------------------------

In some very specific circumstances, the module name might be ``None`` and the filename and function name might be ``"<unknown>"``.

.. code-block:: none

    2024-12-01 16:23:21.769 | INFO     | None:<unknown>:0 - Message from unknown source.

Such a situation indicates that the ``logger`` was unable to retrieve the caller's context. In particular, this can happen when Loguru is used with Dask or Cython. In such cases, this behavior is normal, and there is nothing to do unless you wish to implement a custom |patch| function::

    logger = logger.patch(lambda record: record.update(name="my_module"))

This issue may also result from improper use of the ``depth`` argument of the |opt| method. Make sure that the value of this argument is correct.


Why can't I access the ``Logger`` class and other types at runtime?
-------------------------------------------------------------------

The ``logger`` object imported from the ``loguru`` library is an instance of the |Logger| class. However, you should not attempt to instantiate a logger yourself. The |Logger| class is not public and will be unusable by your Python application. It is therefore expected that the following code will raise an error::

    from loguru import Logger
    # Output: ImportError: cannot import name 'Logger' from 'loguru'

It is only possible to use the |Logger| class in the context of type hints. In such cases, no error will be raised. Said otherwise, that means only type checkers can access the |Logger| class. Below is an example of how to use ``Logger`` for typing purposes, but without runtime access::

    from __future__ import annotations

    import typing

    from loguru import logger

    if typing.TYPE_CHECKING:
        from loguru import Logger

    def my_function(logger: Logger):
        logger.info("Hello, World!")

If for some reason you need to perform type checking at runtime, you can make a comparison with the type on the ``logger`` instance::

    import loguru
    import logging

    def my_function(logger: loguru.Logger | logging.Logger):
        if isinstance(logger, type(loguru.logger)):
            logger.info("Hello, {}!", "World")
        else:
            logger.info("Hello, %s!", "World")

.. seealso::

   :ref:`Type hints <type-hints>`
