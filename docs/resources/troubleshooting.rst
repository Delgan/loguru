Common questions and troubleshooting tips for ``loguru``
========================================================

.. highlight:: python3


How do I configure the logger?
------------------------------

Configure your logger at the entry point of your application. Import the logger within modules to prevent configuration issues.


Why are my logs duplicated in the output?
-----------------------------------------

Multiple imports of logger in different modules can cause duplication. Configure the logger in a single module and import it elsewhere.


Why are my logs not appearing in the output?
--------------------------------------------

Ensure that you've added at least one sink using logger.add(). Check the logging level; messages below the set level won't appear.


How to prevent performance issues with logging?
-----------------------------------------------

Extensive logging can slow down your application. Use appropriate logging levels in production (WARNING or higher).


How to log to multiple destinations (sinks)?
--------------------------------------------

You can add multiple sinks to the logger to direct logs to different destinations:

.. code::

    logger.add("file.log", rotation="500 MB")  # Log to a file, rotating every 500 MB
    logger.add(sys.stderr, format="{time} - {level} - {message}")  # Log to stderr with custom format
