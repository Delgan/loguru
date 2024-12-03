.. _type-hints:

Type Hints
==========

.. |str| replace:: :class:`str`
.. |namedtuple| replace:: :func:`namedtuple<collections.namedtuple>`
.. |dict| replace:: :class:`dict`

.. |Logger| replace:: :class:`~loguru._logger.Logger`
.. |catch| replace:: :meth:`~loguru._logger.Logger.catch()`
.. |contextualize| replace:: :meth:`~loguru._logger.Logger.contextualize()`
.. |complete| replace:: :meth:`~loguru._logger.Logger.complete()`
.. |bind| replace:: :meth:`~loguru._logger.Logger.bind()`
.. |patch| replace:: :meth:`~loguru._logger.Logger.patch()`
.. |opt| replace:: :meth:`~loguru._logger.Logger.opt()`
.. |level| replace:: :meth:`~loguru._logger.Logger.level()`

.. _stub file: https://www.python.org/dev/peps/pep-0484/#stub-files
.. _string literals: https://www.python.org/dev/peps/pep-0484/#forward-references
.. _postponed evaluation of annotations: https://www.python.org/dev/peps/pep-0563/
.. |future| replace:: ``__future__``
.. _future: https://www.python.org/dev/peps/pep-0563/#enabling-the-future-behavior-in-python-3-7
.. |loguru-mypy| replace:: ``loguru-mypy``
.. _loguru-mypy: https://github.com/kornicameister/loguru-mypy
.. |documentation of loguru-mypy| replace:: documentation of ``loguru-mypy``
.. _documentation of loguru-mypy:
    https://github.com/kornicameister/loguru-mypy/blob/master/README.md
.. _@kornicameister: https://github.com/kornicameister

Loguru relies on a `stub file`_ to document its types. This implies that these types are not
accessible during execution of your program, however they can be used by type checkers and IDE.
Also, this means that your Python interpreter has to support `postponed evaluation of annotations`_
to prevent error at runtime. This is achieved with a |future|_ import in Python 3.7+ or by using
`string literals`_ for earlier versions.

A basic usage example could look like this:

.. code-block:: python

    from __future__ import annotations

    import loguru
    from loguru import logger

    def good_sink(message: loguru.Message):
        print("My name is", message.record["name"])

    def bad_filter(record: loguru.Record):
        return record["invalid"]

    logger.add(good_sink, filter=bad_filter)


.. code-block::

    $ mypy test.py
    test.py:8: error: TypedDict "Record" has no key 'invalid'
    Found 1 error in 1 file (checked 1 source file)

There are several internal types to which you can be exposed using Loguru's public API, they are
listed here and might be useful to type hint your code:

- ``Logger``: the usual |logger| object (also returned by |opt|, |bind| and |patch|).
- ``Message``: the formatted logging message sent to the sinks (a |str| with ``record``
  attribute).
- ``Record``: the |dict| containing all contextual information of the logged message.
- ``Level``: the |namedtuple| returned by |level| (with ``name``, ``no``, ``color`` and ``icon``
  attributes).
- ``Catcher``: the context decorator returned by |catch|.
- ``Contextualizer``: the context decorator returned by |contextualize|.
- ``AwaitableCompleter``: the awaitable object returned by |complete|.
- ``RecordFile``: the ``record["file"]`` with ``name`` and ``path`` attributes.
- ``RecordLevel``: the ``record["level"]`` with ``name``, ``no`` and ``icon`` attributes.
- ``RecordThread``: the ``record["thread"]`` with ``id`` and ``name`` attributes.
- ``RecordProcess``: the ``record["process"]`` with ``id`` and ``name`` attributes.
- ``RecordException``: the ``record["exception"]`` with ``type``, ``value`` and ``traceback``
  attributes.

If that is not enough, one can also use the |loguru-mypy|_ library developed by `@kornicameister`_.
Plugin can be installed separately using::

    pip install loguru-mypy

It helps to catch several possible runtime errors by performing additional checks like:

- ``opt(lazy=True)`` loggers accepting only ``typing.Callable[[], typing.Any]`` arguments
- ``opt(record=True)`` loggers wrongly calling log handler like so ``logger.info(..., record={})``
- and even more...

For more details, go to official |documentation of loguru-mypy|_.


See also: :ref:`type-hints-source`.
