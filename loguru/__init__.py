"""
The Loguru library provides pre-instanced objects to facilitate dealing with logging in Python.

Pick one: ``from loguru import logger, notifier, parser``
"""
import atexit as _atexit
import sys as _sys

from . import _defaults
from ._logger import Logger as _Logger
from ._notifier import Notifier as _Notifier
from ._parser import Parser as _Parser

__version__ = "0.1.0"

logger = _Logger({}, None, False, False, False, False, 0)
notifier = _Notifier()
parser = _Parser()

if _defaults.LOGURU_AUTOINIT and _sys.stderr:
    logger.start(_sys.stderr)

_atexit.register(logger.stop)
