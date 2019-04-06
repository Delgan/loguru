Unreleased
==========

- Modify behavior of sink option ``backtrace`` so it only extends the stacktrace upward, the display of variables values is now controlled with the new ``diagnose`` argument (`#49 <https://github.com/Delgan/loguru/issues/49>`_)
- Add coloration of exception traceback even if ``diagnose`` and ``backtrace`` options are ``False``
- The ``record["exception"]`` attribute is now unpackable as a ``(type, value, traceback)`` tuple
- Fix exception stack trace not colorizing source code lines on Windows
- Fix possible ``AttributeError`` while formatting exceptions within a ``celery`` task (`#52 <https://github.com/Delgan/loguru/issues/52>`_)
- Fix `logger.catch` decorator not working with generator, coroutine functions (`#75 <https://github.com/Delgan/loguru/issues/75>`_)


0.2.5 (2019-01-20)
==================

- Modify behavior of sink option ``backtrace=False`` so it doesn't extend traceback upward automatically (`#30 <https://github.com/Delgan/loguru/issues/30>`_)
- Fix import error on some platforms using Python 3.5 with limited ``localtime()`` support (`#33 <https://github.com/Delgan/loguru/issues/33>`_)
- Fix incorrect time formatting of locale month using ``MMM`` and ``MMMM`` tokens (`#34 <https://github.com/Delgan/loguru/pull/34>`_, thanks `@nasyxx <https://github.com/nasyxx>`_)
- Fix race condition permitting to write on a stopped handler


0.2.4 (2018-12-26)
==================

- Fix adding handler while logging which was not thread-safe (`#22 <https://github.com/Delgan/loguru/issues/22>`_)


0.2.3 (2018-12-16)
==================

- Add support for PyPy
- Add support for Python 3.5
- Fix incompatibility with ``awscli`` by downgrading required ``colorama`` dependency version (`#12 <https://github.com/Delgan/loguru/issues/12>`_)


0.2.2 (2018-12-12)
==================

- Deprecate ``logger.start()`` and ``logger.stop()`` methods in favor of ``logger.add()`` and ``logger.remove()`` (`#3 <https://github.com/Delgan/loguru/issues/3>`_)
- Fix ignored formatting while using ``logging.Handler`` sinks (`#4 <https://github.com/Delgan/loguru/issues/4>`_)
- Fix impossibility to set empty environment variable color on Windows (`#7 <https://github.com/Delgan/loguru/issues/7>`_)


0.2.1 (2018-12-08)
==================

- Fix typo preventing README to be correctly displayed on PyPI


0.2.0 (2018-12-08)
==================

- Remove the ``parser`` and refactor it into the ``logger.parse()`` method
- Remove the ``notifier`` and its dependencies, just ``pip install notifiers`` if user needs it


0.1.0 (2018-12-07)
==================

- Add logger
- Add notifier
- Add parser


0.0.1 (2017-09-04)
==================

Initial release
