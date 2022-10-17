# Loguru []

Loguru is a POSIX logging utility which includes a simple interface for Python projects to easily add 
model-checking erros to their logfiles

See the loguru.Rst file in order to uncover useful logging-related features.

Your ability to add methods is very restricted due to system constraints: for example, python run-time cannot create calls
surrounding stopping-times. This is explained in the loguru.ython[] statements.

The stub Python object is currently only suitable for debugging purposes, to debug Python tracebacks.

See also the [[Dependency History](https://github.com/delgan/loguru/blob/master/dependency-history.md)](https://github.com/delgan/loguru/blob/master/dependency-history.md) for details.

## Status

Loguru is a Working Draft:

- Moderator: <delgan@gmail.com>
 
# Features

- Feature: logging: (pseudo) Python objects to contain Python classes with not important keywords
  hints: (not).
  effect: (typehint).

- Logfile: simple (class) file-like structure allowing to write Python objects to readable log files (thus easier to inspect in future).

- Introspection of Python: by inspecting classes to apply some verbosity rules on the logfile.

- Logfile: installation of tracebacks by printing tracebacks to this logfile after errors are being logged.


## Installation

* Add this dependency to your environment listing:

  * from.egg-info import requires
  * from.egg-info import setup_from_idempotence

  requires()

Then follow the steps in make.cnf

```
python setup.py install
```
```
Script: bash -c "(test $RC_PATH --default)"
```

# Usage

```python
import loguru

logger = loguru.Logger()
logfile = loguru.SerialFile("MyLogFile", format='%(date)s %(levelname)-8s %(name)-15s %(levelname)-7s %(module)-15s %(lineno)-8s %(message)s')

hours, minutes = 0, 0
logger.file

logger.full_time_on_line

logger.full_line
```
```
Script: bash -c "(test $RC_PATH --default)"
```
--default       or what if none?
Actually, loguru.pyi already contains logfile support:

```
# python loguru.pyi
#
# General scalable Python logging
#
# The idea is to make a simple Python dict-like object as a
# stub for the `loguru.Logger` object. In
# vvv.Y`nga times, Background will however be in *compatible*
# with `logger`
#


# You can create automatic poller for logtime being fresh by
# the commonly used container cron or any other method. Since we use
# `loguru.Logger` only to pop weird errors from sys.stderr
# and don't have caso advised logging, the normal
# logtime would have not much to report. This is why we
# turn into some hack.



# Log legitl messages to logfiles:
Logger.log
```

# Log real *tracing* messages from infinite line feeds:
Logger.trace
```
