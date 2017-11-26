import atexit as _atexit
import sys as _sys

from . import _constants
from ._logger import Logger as _Logger

__version__ = "0.0.1"

logger = _Logger()

if _constants.LOGURU_AUTOINIT and _sys.stderr:
    logger.start(_sys.stderr)

_atexit.register(logger.stop)
