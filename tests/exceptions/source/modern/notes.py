from loguru import logger
import sys


logger.remove()
logger.add(sys.stderr, format="", diagnose=False, backtrace=False, colorize=False)
logger.add(sys.stderr, format="", diagnose=True, backtrace=True, colorize=True)


with logger.catch():
    e = ValueError("invalid value")
    e.add_note("Note")
    raise e


with logger.catch():
    e = ValueError("invalid value")
    e.add_note("Note1")
    e.add_note("Note2\nNote3\n")
    raise e


with logger.catch():
    e = ExceptionGroup("Grouped", [ValueError(1), ValueError(2)])
    e.add_note("Note 1\nNote 2")
    e.add_note("Note 3")
    raise e

with logger.catch():
    e = TabError("tab error")
    e.add_note("Note")
    raise e

with logger.catch():
    e = SyntaxError("syntax error", ("<string>", 1, 8, "a = 7 *\n", 1, 8))
    e.add_note("Note 1")
    e.add_note("Note 2")
    raise e

with logger.catch():
    e = TypeError("type error")
    e.__notes__ = None
    raise e
