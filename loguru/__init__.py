"""
The Loguru library provides a pre-instanced logger to facilitate dealing with logging in Python.

Just ``from loguru import logger``.
"""
import atexit as _atexit
import sys as _sys

from . import _defaults
from ._logger import Logger as _Logger

__version__ = "0.2.5"

logger = _Logger({}, None, False, False, False, False, 0)

if _defaults.LOGURU_AUTOINIT and _sys.stderr:
    logger.add(_sys.stderr)

_atexit.register(logger.remove)
