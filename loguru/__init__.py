"""
The Loguru library provides a pre-instanced logger to facilitate dealing with logging in Python.

Just ``from loguru import logger``.
"""
import atexit as _atexit
import sys as _sys

from . import _defaults
from ._logger import Logger as _Logger

__version__ = "0.3.2"

__all__ = ["logger"]

logger = _Logger(None, 0, False, False, False, False, None, {})

if _defaults.LOGURU_AUTOINIT and _sys.stderr:
    logger.add(_sys.stderr)

_atexit.register(logger.remove)
