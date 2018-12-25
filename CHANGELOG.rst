Unreleased
==========

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
