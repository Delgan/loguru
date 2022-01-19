Switching from standard ``logging`` to ``loguru``
=================================================

.. highlight:: python3

.. |getLogger| replace:: :func:`~logging.getLogger`
.. |addLevelName| replace:: :func:`~logging.addLevelName`
.. |getLevelName| replace:: :func:`~logging.getLevelName`
.. |Handler| replace:: :class:`~logging.Handler`
.. |Logger| replace:: :class:`~logging.Logger`
.. |Filter| replace:: :class:`~logging.Filter`
.. |Formatter| replace:: :class:`~logging.Formatter`
.. |LoggerAdapter| replace:: :class:`~logging.LoggerAdapter`
.. |logger.setLevel| replace:: :meth:`~logging.Logger.setLevel`
.. |logger.addFilter| replace:: :meth:`~logging.Logger.addFilter`
.. |makeRecord| replace:: :meth:`~logging.Logger.makeRecord`
.. |disable| replace:: :meth:`~logging.Logger.disable`
.. |propagate| replace:: :attr:`~logging.Logger.propagate`
.. |addHandler| replace:: :meth:`~logging.Logger.addHandler`
.. |removeHandler| replace:: :meth:`~logging.Logger.removeHandler`
.. |handle| replace:: :meth:`~logging.Handler.handle`
.. |emit| replace:: :meth:`~logging.Handler.emit`
.. |handler.setLevel| replace:: :meth:`~logging.Handler.setLevel`
.. |handler.addFilter| replace:: :meth:`~logging.Handler.addFilter`
.. |setFormatter| replace:: :meth:`~logging.Handler.setFormatter`
.. |createLock| replace:: :meth:`~logging.Handler.createLock`
.. |acquire| replace:: :meth:`~logging.Handler.acquire`
.. |release| replace:: :meth:`~logging.Handler.release`
.. |isEnabledFor| replace:: :meth:`~logging.Logger.isEnabledFor`
.. |dictConfig| replace:: :func:`~logging.config.dictConfig`
.. |basicConfig| replace:: :func:`~logging.basicConfig`

.. |add| replace:: :meth:`~loguru._logger.Logger.add()`
.. |remove| replace:: :meth:`~loguru._logger.Logger.remove()`
.. |bind| replace:: :meth:`~loguru._logger.Logger.bind`
.. |opt| replace:: :meth:`~loguru._logger.Logger.opt()`
.. |level| replace:: :meth:`~loguru._logger.Logger.level()`
.. |configure| replace:: :meth:`~loguru._logger.Logger.configure()`

.. |pytest| replace:: ``pytest``
.. _pytest: https://docs.pytest.org/en/latest/
.. |caplog| replace:: ``caplog``
.. _caplog: https://docs.pytest.org/en/latest/logging.html?highlight=caplog#caplog-fixture

.. _`GH#59`: https://github.com/Delgan/loguru/issues/59
.. _`GH#474`: https://github.com/Delgan/loguru/issues/474



Fundamental differences between ``logging`` and ``loguru``
----------------------------------------------------------

Although ``loguru`` is written "from scratch" and does not rely on standard ``logging`` internally, both libraries serve the same purpose: provide functionalities to implement a flexible event logging system. The main difference is that standard ``logging`` requires the user to explicitly instantiate named ``Logger`` and configure them with ``Handler``, ``Formatter`` and ``Filter``, while ``loguru`` tries to narrow down the amount of configuration steps.

Apart from that, usage is globally the same, once the ``logger`` object is created or imported you can start using it to log messages with the appropriate severity (``logger.debug("Dev message")``, ``logger.warning("Danger!")``, etc.), messages which are then sent to the configured handlers.

As for standard logging, default logs are sent to ``sys.stderr`` rather than ``sys.stdout``. The POSIX standard specifies that  ``stderr`` is the correct stream for "diagnostic output". The main compelling case in favor or logging to ``stderr`` is that it avoids mixing the actual output of the application with debug information. Consider for example pipe-redirection like ``python my_app.py | other_app`` which would not be possible if logs were emitted to ``stdout``. Another major benefit is that Python resolves encoding issues on ``sys.stderr`` by escaping faulty characters (``"backslashreplace"`` policy) while it raises an ``UnicodeEncodeError`` (``"strict"`` policy) on ``sys.stdout``.


Replacing ``getLogger()`` function
----------------------------------

It is usual to call |getLogger| at the beginning of each file to retrieve and use a logger across your module, like this: ``logger = logging.getLogger(__name__)``.

Using Loguru, there is no need to explicitly get and name a logger, ``from loguru import logger`` suffices. Each time this imported logger is used, a :ref:`record <record>` is created and will automatically contain the contextual ``__name__`` value.

As for standard logging, the ``name`` attribute can then be used to format and filter your logs.


Replacing ``Logger`` objects
----------------------------

Loguru replaces the standard |Logger| configuration by a proper :ref:`sink <sink>` definition. Instead of configuring a logger, you should |add| and parametrize your handlers. The |logger.setLevel| and |logger.addFilter| are suppressed by the configured sink ``level`` and ``filter`` parameters. The |propagate| attribute and |disable| method can be replaced by the ``filter`` option too. The |makeRecord| method can be replaced using the ``record["extra"]`` dict.

Sometimes, more fine-grained control is required over a particular logger. In such case, Loguru provides the |bind| method which can be in particular used to generate a specifically named logger.

For example, by calling ``other_logger = logger.bind(name="other")``, each :ref:`message <message>` logged using ``other_logger`` will populate the ``record["extra"]`` dict with the ``name`` value, while using ``logger`` won't. This permits differentiating logs from ``logger`` or ``other_logger`` from within your sink or filter function.

Let suppose you want a sink to log only some very specific messages::

    def specific_only(record):
        return "specific" in record["extra"]

    logger.add("specific.log", filter=specific_only)

    specific_logger = logger.bind(specific=True)

    logger.info("General message")          # This is filtered-out by the specific sink
    specific_logger.info("Module message")  # This is accepted by the specific sink (and others)

Another example, if you want to attach one sink to one named logger::

    # Only write messages from "a" logger
    logger.add("a.log", filter=lambda record: record["extra"].get("name") == "a")
    # Only write messages from "b" logger
    logger.add("b.log", filter=lambda record: record["extra"].get("name") == "b")

    logger_a = logger.bind(name="a")
    logger_b = logger.bind(name="b")

    logger_a.info("Message A")
    logger_b.info("Message B")


Replacing ``Handler``, ``Filter`` and ``Formatter`` objects
-----------------------------------------------------------

Standard ``logging`` requires you to create an |Handler| object and then call |addHandler|. Using Loguru, the handlers are started using |add|. The sink defines how the handler should manage incoming logging messages, as would do |handle| or |emit|. To log from multiple modules, you just have to import the logger, all messages will be dispatched to the added handlers.

While calling |add|, the ``level`` parameter replaces |handler.setLevel|, the ``format`` parameter replaces |setFormatter|, the ``filter`` parameter replaces |handler.addFilter|. The thread-safety is managed automatically by Loguru, so there is no need for |createLock|, |acquire| nor |release|. The equivalent method of |removeHandler| is |remove| which should be used with the identifier returned by |add|.

Note that you don't necessarily need to replace your |Handler| objects because |add| accepts them as valid sinks.

In short, you can replace::

    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler("spam.log")
    fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

With::

    fmt = "{time} - {name} - {level} - {message}"
    logger.add("spam.log", level="DEBUG", format=fmt)
    logger.add(sys.stderr, level="ERROR", format=fmt)


Replacing ``%`` style formatting of messages
--------------------------------------------

Loguru only supports ``{}``-style formatting.

You have to replace ``logger.debug("Some variable: %s", var)`` with ``logger.debug("Some variable: {}", var)``. All ``*args`` and ``**kwargs`` passed to a logging function are used to call ``message.format(*args, **kwargs)``. Arguments which do not appear in the message string are simply ignored. Note that passing arguments to logging functions like this may be useful to (slightly) improve performances: it avoids formatting the message if the level is too low to pass any configured handler.

For converting the general format used by |Formatter|, refer to :ref:`list of available record tokens <record>`.

For converting the date format used by ``datefmt``, refer to :ref:`list of available date tokens<time>`.


Replacing ``exc_info`` argument
-------------------------------

While calling standard logging function, you can pass ``exc_info`` as an argument to add stacktrace to the message. Instead of that, you should use the |opt| method with ``exception`` parameter, replacing ``logger.debug("Debug error:", exc_info=True)`` with ``logger.opt(exception=True).debug("Debug error:")``.

The formatted exception will include the whole stacktrace and variables. To prevent that, make sure to use ``backtrace=False`` and ``diagnose=False`` while adding your sink.


Replacing ``extra`` argument and ``LoggerAdapter`` objects
----------------------------------------------------------

To pass contextual information to log messages, replace ``extra`` by inlining |bind| method::

    context = {"clientip": "192.168.0.1", "user": "fbloggs"}

    logger.info("Protocol problem", extra=context)   # Standard logging
    logger.bind(**context).info("Protocol problem")  # Loguru

This will add context information to the ``record["extra"]`` dict of your logged message, so make sure to configure your handler format adequately::

    fmt = "%(asctime)s %(clientip)s %(user)s %(message)s"     # Standard logging
    fmt = "{time} {extra[clientip]} {extra[user]} {message}"  # Loguru

You can also replace |LoggerAdapter| by calling ``logger = logger.bind(clientip="192.168.0.1")`` before using it, or by assigning the bound logger to a class instance::

    class MyClass:

        def __init__(self, clientip):
            self.logger = logger.bind(clientip=clientip)

        def func(self):
            self.logger.debug("Running func")


Replacing ``isEnabledFor()`` method
-----------------------------------

If you wish to log useful information for your debug logs, but don't want to pay the performance penalty in release mode while no debug handler is configured, standard logging provides the |isEnabledFor| method::

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Message data: %s", expensive_func())

You can replace this with the |opt| method and ``lazy`` option::

    # Arguments should be functions which will be called if needed
    logger.opt(lazy=True).debug("Message data: {}", expensive_func)


Replacing ``addLevelName()`` and ``getLevelName()`` functions
-------------------------------------------------------------

To add a new custom level, you can replace |addLevelName| with the |level| function::

    logging.addLevelName(33, "CUSTOM")                       # Standard logging
    logger.level("CUSTOM", no=45, color="<red>", icon="🚨")  # Loguru

The same function can be used to replace |getLevelName|::

    logger.getLevelName(33)  # => "CUSTOM"
    logger.level("CUSTOM")   # => (name='CUSTOM', no=33, color="<red>", icon="🚨")

Note that contrary to standard logging, Loguru doesn't associate severity number to any level, levels are only identified by their name.


Replacing ``basicConfig()`` and ``dictConfig()`` functions
----------------------------------------------------------

The |basicConfig| and |dictConfig| functions are replaced by the |configure| method.

This does not accept ``config.ini`` files, though, so you have to handle that yourself using your favorite format.


Making things work with Pytest and caplog
-----------------------------------------

|pytest|_ is a very common testing framework. The |caplog|_ fixture captures logging output so that it can be tested against. For example::

    # `some_func` adds two numbers, and logs a warning if the first is < 1
    def test_some_func_logs_warning(caplog):
        assert some_func(-1, 3) == 2
        assert "Oh no!" in caplog.text

If you've followed all the migration guidelines thus far, you'll notice that this test will fail. This is because |pytest|_ links to the standard library's ``logging`` module.

So to fix things, we need to add a sink that propagates Loguru to the caplog handler.
This is done by overriding the |caplog|_ fixture to capture its handler. In your ``conftest.py`` file, add the following::

    import pytest
    from loguru import logger
    from _pytest.logging import LogCaptureFixture

    @pytest.fixture
    def caplog(caplog: LogCaptureFixture):
        handler_id = logger.add(caplog.handler, format="{message}")
        yield caplog
        logger.remove(handler_id)

Run your tests and things should all be working as expected. Additional information can be found in `GH#59`_ and `GH#474`_.
