import sys as _sys

from ._logger import Logger as _Logger

__version__ = "0.0.1"

logger = _Logger()
logger.log_to(_sys.stderr)
