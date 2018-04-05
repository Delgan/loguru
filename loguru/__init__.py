import atexit as _atexit
import sys as _sys

from . import _defaults
from ._logger import Logger as _Logger

__version__ = "0.0.1"

logger = _Logger({}, [], None, False, False, False, 0)

if _defaults.LOGURU_AUTOINIT and _sys.stderr:
    logger.start(_sys.stderr)

_atexit.register(logger.stop)
