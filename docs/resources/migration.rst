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

Replacing ``getLogger()`` function
----------------------------------

It is usual to call |getLogger| at the beginning of each file to retrieve and use a logger across your module, like this: ``logger = logging.getLogger(__name__)``.

Using Loguru, there is no need to explicitly get and name a logger, ``from loguru import logger`` suffices. Each time this imported logger is used, a :ref:`record <record>` is created and will automatically contain the contextual ``__name__`` value.

As for standard logging, the ``name`` attribute can then be used to format and filter your logs.


Replacing ``Logger`` objects
----------------------------

Loguru replaces the standard |Logger| configuration by a proper :ref:`sink <sink>` definition. Instead of configuring a logger, you should |add| and parametrize your handlers. The |logger.setLevel| and |logger.addFilter| are suppressed by the configured sink ``level`` and ``filter`` parameters. The |propagate| attribute and |disable| method can be replaced by the ``filter`` option too. The |makeRecord| method can be replaced using the ``record["extra"]`` dict.

Sometimes, more fine-grained control is required over a particular logger. In such case, Loguru provides the |bind| method which can be in particular used to generate a specifically named logger.

For example, by calling ``other_logger = logger.bind(name="other")``, each :ref:`message <message>` logged using ``other_logger`` will populate the ``record["extra"]`` dict with the ``name`` value, while using ``logger`` won't. This permits to differentiate logs from ``logger`` or ``other_logger`` from within your sink or filter function.

Let suppose you want a sink to log only some very specific messages::

    logger.start("specific.log", filter=lambda record: "specific" in record["extra"])

    specific_logger = logger.bind(specific=True)

    logger.info("General message")          # This is filtered-out by the specific sink
    specific_logger.info("Module message")  # This is accepted by the specific sink (and others)

Another example, if you want to attach one sink to one named logger::

    # Only write messages from "a" logger
    logger.start("a.log", filter=lambda record: record["extra"].get("name") == "a")
    # Only write messages from "b" logger
    logger.start("b.log", filter=lambda record: record["extra"].get("name") == "b")

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

    fmt = "{time} - {name} - {level} - {messae}"
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

The formatted exception will include the whole stacktrace and variables. To prevent that, make sure to use ``backtrace=False`` while adding your sink.


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
    logger.level("CUSTOM")   # => (no=33, color="<red>", icon="🚨")

Note that contrary to standard logging, Loguru doesn't associate severity number to any level, levels are only identified by their name.


Replacing ``basicConfig()`` and ``dictConfig()`` functions
----------------------------------------------------------

The |basicConfig| and |dictConfig| functions are replaced by the |configure| method.

This does not accept ``config.ini`` files, though, so you have to handle that yourself using your favorite format.
