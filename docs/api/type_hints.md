(type-hints)=
# Type Hints

Loguru relies on a [stub file](https://www.python.org/dev/peps/pep-0484/#stub-files) to document its types. This implies that these types are not
accessible during execution of your program, however they can be used by type checkers and IDE.
Also, this means that your Python interpreter has to support [postponed evaluation of annotations](https://www.python.org/dev/peps/pep-0563/)
to prevent error at runtime. This is achieved with a [`__future__`](https://www.python.org/dev/peps/pep-0563/#enabling-the-future-behavior-in-python-3-7) import in Python 3.7+ or by using
[string literals](https://www.python.org/dev/peps/pep-0484/#forward-references) for earlier versions.

A basic usage example could look like this:

```python
from __future__ import annotations

import loguru
from loguru import logger

def good_sink(message: loguru.Message):
    print("My name is", message.record["name"])

def bad_filter(record: loguru.Record):
    return record["invalid"]

logger.add(good_sink, filter=bad_filter)
```

```text
$ mypy test.py
test.py:8: error: TypedDict "Record" has no key 'invalid'
Found 1 error in 1 file (checked 1 source file)
```

There are several internal types to which you can be exposed using Loguru's public API, they are
listed here and might be useful to type hint your code:

- `Logger`: the usual `logger` object (also returned by {meth}`~loguru._logger.Logger.opt()`, {meth}`~loguru._logger.Logger.bind()` and {meth}`~loguru._logger.Logger.patch()`).
- `Message`: the formatted logging message sent to the sinks (a {class}`str` with `record`
  attribute).
- `Record`: the {class}`dict` containing all contextual information of the logged message.
- `Level`: the {func}`namedtuple<collections.namedtuple>` returned by {meth}`~loguru._logger.Logger.level()` (with `name`, `no`, `color` and `icon`
  attributes).
- `Catcher`: the context decorator returned by {meth}`~loguru._logger.Logger.catch()`.
- `Contextualizer`: the context decorator returned by {meth}`~loguru._logger.Logger.contextualize()`.
- `AwaitableCompleter`: the awaitable object returned by {meth}`~loguru._logger.Logger.complete()`.
- `RecordFile`: the `record["file"]` with `name` and `path` attributes.
- `RecordLevel`: the `record["level"]` with `name`, `no` and `icon` attributes.
- `RecordThread`: the `record["thread"]` with `id` and `name` attributes.
- `RecordProcess`: the `record["process"]` with `id` and `name` attributes.
- `RecordException`: the `record["exception"]` with `type`, `value` and `traceback`
  attributes.

If that is not enough, one can also use the [`loguru-mypy`](https://github.com/kornicameister/loguru-mypy) library developed by [@kornicameister](https://github.com/kornicameister).
Plugin can be installed separately using:

```bash
pip install loguru-mypy
```

It helps to catch several possible runtime errors by performing additional checks like:

- `opt(lazy=True)` loggers accepting only `typing.Callable[[], typing.Any]` arguments
- `opt(record=True)` loggers wrongly calling log handler like so `logger.info(..., record={})`
- and even more...

For more details, go to official [documentation of `loguru-mypy`](https://github.com/kornicameister/loguru-mypy/blob/master/README.md).

See also: {ref}`type-hints-source`.
