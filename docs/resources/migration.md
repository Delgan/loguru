# Switching from Standard Logging to Loguru

```{highlight} python3
```

## Introduction to logging in Python

First and foremost, it is important to understand some basic concepts about logging in Python.

Logging is an essential part of any application, as it allows you to track the behavior of your code and diagnose issues. It associates messages with severity levels which are collected and dispatched to readable outputs called handlers.

For newcomers, take a look at the tutorial in the Python documentation: [Logging HOWTO](https://docs.python.org/3/howto/logging.html).

## Fundamental differences between `logging` and `loguru`

Although `loguru` is written "from scratch" and does not rely on standard `logging` internally, both libraries serve the same purpose: provide functionalities to implement a flexible event logging system. The main difference is that standard `logging` requires the user to explicitly instantiate named `Logger` and configure them with `Handler`, `Formatter` and `Filter`, while `loguru` tries to narrow down the amount of configuration steps.

Apart from that, usage is globally the same, once the `logger` object is created or imported you can start using it to log messages with the appropriate severity (`logger.debug("Dev message")`, `logger.warning("Danger!")`, etc.), messages which are then sent to the configured handlers.

As for standard logging, default logs are sent to `sys.stderr` rather than `sys.stdout`. The POSIX standard specifies that `stderr` is the correct stream for "diagnostic output". The main compelling case in favor or logging to `stderr` is that it avoids mixing the actual output of the application with debug information. Consider for example pipe-redirection like `python my_app.py | other_app` which would not be possible if logs were emitted to `stdout`. Another major benefit is that Python resolves encoding issues on `sys.stderr` by escaping faulty characters (`"backslashreplace"` policy) while it raises an `UnicodeEncodeError` (`"strict"` policy) on `sys.stdout`.

## Replacing `getLogger()` function

It is usual to call {func}`~logging.getLogger` at the beginning of each file to retrieve and use a logger across your module, like this: `logger = logging.getLogger(__name__)`.

Using Loguru, there is no need to explicitly get and name a logger, `from loguru import logger` suffices. Each time this imported logger is used, a {ref}`record <record>` is created and will automatically contain the contextual `__name__` value.

As for standard logging, the `name` attribute can then be used to format and filter your logs.

## Replacing `Logger` objects

Loguru replaces the standard {class}`~logging.Logger` configuration by a proper {ref}`sink <sink>` definition. Instead of configuring a logger, you should {meth}`~loguru._logger.Logger.add()` and parametrize your handlers. The {meth}`~logging.Logger.setLevel` and {meth}`~logging.Logger.addFilter` are suppressed by the configured sink `level` and `filter` parameters. The {attr}`~logging.Logger.propagate` attribute and {func}`~logging.disable` function can be replaced by the `filter` option too. The {meth}`~logging.Logger.makeRecord` method can be replaced using the `record["extra"]` dict.

Sometimes, more fine-grained control is required over a particular logger. In such case, Loguru provides the {meth}`~loguru._logger.Logger.bind` method which can be in particular used to generate a specifically named logger.

For example, by calling `other_logger = logger.bind(name="other")`, each {ref}`message <message>` logged using `other_logger` will populate the `record["extra"]` dict with the `name` value, while using `logger` won't. This permits differentiating logs from `logger` or `other_logger` from within your sink or filter function.

Let suppose you want a sink to log only some very specific messages:

```python
def specific_only(record):
    return "specific" in record["extra"]

logger.add("specific.log", filter=specific_only)

specific_logger = logger.bind(specific=True)

logger.info("General message")          # This is filtered-out by the specific sink
specific_logger.info("Module message")  # This is accepted by the specific sink (and others)
```

Another example, if you want to attach one sink to one named logger:

```python
# Only write messages from "a" logger
logger.add("a.log", filter=lambda record: record["extra"].get("name") == "a")
# Only write messages from "b" logger
logger.add("b.log", filter=lambda record: record["extra"].get("name") == "b")

logger_a = logger.bind(name="a")
logger_b = logger.bind(name="b")

logger_a.info("Message A")
logger_b.info("Message B")
```

## Replacing `Handler`, `Filter` and `Formatter` objects

Standard `logging` requires you to create an {class}`~logging.Handler` object and then call {meth}`~logging.Logger.addHandler`. Using Loguru, the handlers are started using {meth}`~loguru._logger.Logger.add()`. The sink defines how the handler should manage incoming logging messages, as would do {meth}`~logging.Handler.handle` or {meth}`~logging.Handler.emit`. To log from multiple modules, you just have to import the logger, all messages will be dispatched to the added handlers.

While calling {meth}`~loguru._logger.Logger.add()`, the `level` parameter replaces {meth}`~logging.Handler.setLevel`, the `format` parameter replaces {meth}`~logging.Handler.setFormatter`, the `filter` parameter replaces {meth}`~logging.Handler.addFilter`. The thread-safety is managed automatically by Loguru, so there is no need for {meth}`~logging.Handler.createLock`, {meth}`~logging.Handler.acquire` nor {meth}`~logging.Handler.release`. The equivalent method of {meth}`~logging.Logger.removeHandler` is {meth}`~loguru._logger.Logger.remove()` which should be used with the identifier returned by {meth}`~loguru._logger.Logger.add()`.

Note that you don't necessarily need to replace your {class}`~logging.Handler` objects because {meth}`~loguru._logger.Logger.add()` accepts them as valid sinks.

In short, you can replace:

```python
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
```

With:

```python
fmt = "{time} - {name} - {level} - {message}"
logger.add("spam.log", level="DEBUG", format=fmt)
logger.add(sys.stderr, level="ERROR", format=fmt)
```

## Replacing `LogRecord` objects

In Loguru, the equivalence of a {class}`~logging.LogRecord` instance is a simple `dict` which stores the details of a logged message. To find the correspondence with {class}`~logging.LogRecord` attributes, please refer to {ref}`the "record dict" documentation <record>` which lists all available keys.

This `dict` is attached to each {ref}`logged message <message>` through a special `record` attribute of the `str`-like object received by sinks. For example:

```python
def simple_sink(message):
    # A simple sink can use "message" as a basic string and ignore the "record" attribute.
    print(message, end="")

def advanced_sink(message):
    # An advanced sink can use the "record" attribute to access contextual information.
    record = message.record

    if record["level"].no >= 50:
        file_path = record["file"].path
        print(f"Critical error in {file_path}", end="", file=sys.stderr)
    else:
        print(message, end="")

logger.add(simple_sink)
logger.add(advanced_sink)
```

As explained in the previous sections, the record dict is also available during invocation of filtering and formatting functions.

If you need to extend the record dict with custom information similarly to what was possible with {func}`~logging.setLogRecordFactory`, you can simply use the {meth}`~loguru._logger.Logger.patch` method to add the desired keys to the `record["extra"]` dict.

## Replacing `%` style formatting of messages

Loguru only supports `{}`-style formatting.

You have to replace `logger.debug("Some variable: %s", var)` with `logger.debug("Some variable: {}", var)`. All `*args` and `**kwargs` passed to a logging function are used to call `message.format(*args, **kwargs)`. Arguments which do not appear in the message string are simply ignored. Note that passing arguments to logging functions like this may be useful to (slightly) improve performances: it avoids formatting the message if the level is too low to pass any configured handler.

For converting the general format used by {class}`~logging.Formatter`, refer to {ref}`list of available record tokens <record>`.

For converting the date format used by `datefmt`, refer to {ref}`list of available date tokens<time>`.

## Replacing `exc_info` argument

While calling standard logging function, you can pass `exc_info` as an argument to add stacktrace to the message. Instead of that, you should use the {meth}`~loguru._logger.Logger.opt()` method with `exception` parameter, replacing `logger.debug("Debug error:", exc_info=True)` with `logger.opt(exception=True).debug("Debug error:")`.

The formatted exception will include the whole stacktrace and variables. To prevent that, make sure to use `backtrace=False` and `diagnose=False` while adding your sink.

## Replacing `extra` argument and `LoggerAdapter` objects

To pass contextual information to log messages, replace `extra` by inlining {meth}`~loguru._logger.Logger.bind` method:

```python
context = {"clientip": "192.168.0.1", "user": "fbloggs"}

logger.info("Protocol problem", extra=context)   # Standard logging
logger.bind(**context).info("Protocol problem")  # Loguru
```

This will add context information to the `record["extra"]` dict of your logged message, so make sure to configure your handler format adequately:

```python
fmt = "%(asctime)s %(clientip)s %(user)s %(message)s"     # Standard logging
fmt = "{time} {extra[clientip]} {extra[user]} {message}"  # Loguru
```

You can also replace {class}`~logging.LoggerAdapter` by calling `logger = logger.bind(clientip="192.168.0.1")` before using it, or by assigning the bound logger to a class instance:

```python
class MyClass:

    def __init__(self, clientip):
        self.logger = logger.bind(clientip=clientip)

    def func(self):
        self.logger.debug("Running func")
```

## Replacing `isEnabledFor()` method

If you wish to log useful information for your debug logs, but don't want to pay the performance penalty in release mode while no debug handler is configured, standard logging provides the {meth}`~logging.Logger.isEnabledFor` method:

```python
if logger.isEnabledFor(logging.DEBUG):
    logger.debug("Message data: %s", expensive_func())
```

You can replace this with the {meth}`~loguru._logger.Logger.opt()` method and `lazy` option:

```python
# Arguments should be functions which will be called if needed
logger.opt(lazy=True).debug("Message data: {}", expensive_func)
```

## Replacing `addLevelName()` and `getLevelName()` functions

To add a new custom level, you can replace {func}`~logging.addLevelName` with the {meth}`~loguru._logger.Logger.level()` function:

```python
logging.addLevelName(33, "CUSTOM")                       # Standard logging
logger.level("CUSTOM", no=45, color="<red>", icon="🚨")  # Loguru
```

The same function can be used to replace {func}`~logging.getLevelName`:

```python
logger.getLevelName(33)  # => "CUSTOM"
logger.level("CUSTOM")   # => (name='CUSTOM', no=33, color="<red>", icon="🚨")
```

Note that contrary to standard logging, Loguru doesn't associate severity number to any level, levels are only identified by their name.

## Replacing `basicConfig()` and `dictConfig()` functions

The {func}`~logging.basicConfig` and {func}`~logging.config.dictConfig` functions are replaced by the {meth}`~loguru._logger.Logger.configure()` method.

This does not accept `config.ini` files, though, so you have to handle that yourself using your favorite format.

## Replacing `captureWarnings()` function

The {func}`~logging.captureWarnings` function which redirects alerts from the {mod}`warnings` module to the logging system can be implemented by simply replacing {func}`warnings.showwarning` function as follow:

```python
import warnings
from loguru import logger

showwarning_ = warnings.showwarning

def showwarning(message, *args, **kwargs):
    logger.warning(message)
    showwarning_(message, *args, **kwargs)

warnings.showwarning = showwarning
```

(migration-assert-logs)=
## Replacing `assertLogs()` method from `unittest` library

The {meth}`~unittest.TestCase.assertLogs` method defined in the {mod}`unittest` from standard library is used to capture and test logged messages. However, it can't be made compatible with Loguru. It needs to be replaced with a custom context manager possibly implemented as follows:

```python
from contextlib import contextmanager

@contextmanager
def capture_logs(level="INFO", format="{level}:{name}:{message}"):
    """Capture loguru-based logs."""
    output = []
    handler_id = logger.add(output.append, level=level, format=format)
    yield output
    logger.remove(handler_id)
```

It provides the list of {ref}`logged messages <message>` for each of which you can access {ref}`the record attribute<record>`. Here is a usage example:

```python
def do_something(val):
    if val < 0:
        logger.error("Invalid value")
        return 0
    return val * 2


class TestDoSomething(unittest.TestCase):
    def test_do_something_good(self):
        with capture_logs() as output:
            do_something(1)
        self.assertEqual(output, [])

    def test_do_something_bad(self):
        with capture_logs() as output:
            do_something(-1)
        self.assertEqual(len(output), 1)
        message = output[0]
        self.assertIn("Invalid value", message)
        self.assertEqual(message.record["level"].name, "ERROR")
```

```{seealso}
See {ref}`testing logging <recipes-testing>` for alternative approaches.
```

(migration-caplog)=
## Replacing `caplog` fixture from `pytest` library

[`pytest`](https://docs.pytest.org/en/latest/) is a very common testing framework. The [`caplog`](https://docs.pytest.org/en/latest/logging.html?highlight=caplog#caplog-fixture) fixture captures logging output so that it can be tested against. For example:

```python
from loguru import logger

def some_func(a, b):
    if a < 0:
        logger.warning("Oh no!")
    return a + b

def test_some_func(caplog):
    assert some_func(-1, 3) == 2
    assert "Oh no!" in caplog.text
```

If you've followed all the migration guidelines thus far, you'll notice that this test will fail. This is because [`pytest`](https://docs.pytest.org/en/latest/) links to the standard library's `logging` module.

To ensure compatibility between Loguru and [`pytest`](https://docs.pytest.org/en/latest/), we need to propagate logs to the standard logging handlers used by [`pytest`](https://docs.pytest.org/en/latest/). We simply need to {meth}`~loguru._logger.Logger.add()` these handlers to Loguru's logger using a custom fixture:

- The `caplog_handler` handler which captures logs for inspection in tests using the [`caplog`](https://docs.pytest.org/en/latest/logging.html?highlight=caplog#caplog-fixture) fixture.
- The `log_cli_handler` which outputs logs in live during tests when the `--log-cli-level` flag is used.
- The `report_handler` which displays logs in the terminal summary at the end of tests in case of failures.

In your [`conftest.py`](https://docs.pytest.org/en/latest/reference/fixtures.html#conftest-py-sharing-fixtures-across-multiple-files) file, add the following:

```python
import pytest
from loguru import logger

@pytest.fixture(autouse=True)
def propagate_logs(request):
    """Propagate Loguru logs to standard logging handlers used by Pytest."""
    plugin = request.config.pluginmanager.getplugin("logging-plugin")

    # Remove all existing Loguru handlers, including the default one.
    logger.remove()

    handler_ids = []

    for handler in [plugin.caplog_handler, plugin.log_cli_handler, plugin.report_handler]:

        # Note that, by default, all log levels are propagated to standard handlers.
        # You can adjust the `level` here, modify the handler's level, or use `caplog.set_level()`.
        handler_id = logger.add(handler, format="{message}", level=0)
        handler_ids.append(handler_id)

    yield

    for handler_id in handler_ids:
        logger.remove(handler_id)
```

Run your tests and things should all be working as expected. See also [How to manage logging](https://docs.pytest.org/en/stable/how-to/logging.html) from the official Pytest documentation.

You can also install and use the [`pytest-loguru`](https://github.com/mcarans/pytest-loguru) package created by [@mcarans](https://github.com/mcarans).

```{seealso}
See {ref}`testing logging <recipes-testing>` for alternative approaches.
```
