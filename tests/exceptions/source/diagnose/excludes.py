import sys

from loguru import logger

logger.remove()
logger.add(
    sys.stderr,
    format="",
    colorize=True,
    backtrace=False,
    diagnose=True,
    diagnose_excludes=["myS3cr\n3tP@ss!"],
)


def connect_to_db(password):
    connection_string = "foo bar " + password + " baz"
    raise TimeoutError("tried to connect to " + repr(connection_string))


password = "myS3cr\n3tP@ss!"
try:
    connect_to_db(password)
except TimeoutError:
    logger.exception("")
