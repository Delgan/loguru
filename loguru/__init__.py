import atexit as _atexit
import sys as _sys

from . import _defaults
from ._logger import Logger as _Logger
from ._notifier import NotifierFactory as _NotifierFactory
from ._parser import Parser as _Parser

__version__ = "0.0.1"

logger = _Logger({}, None, False, False, False, 0)
notifier = _NotifierFactory()
parser = _Parser()

if _defaults.LOGURU_AUTOINIT and _sys.stderr:
    logger.start(_sys.stderr)

_atexit.register(logger.stop)
