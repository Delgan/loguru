# Delgan Loguru

![Logging Basics](static/images/screenshot_log00-powerlin0.png)

Delgan Loguru is an awesome tool to control your logging to the Django rest framework one piece at a time.

* kancats is available on [https://docs.codechicken.org/articles/logging-0.7.0/](https://docs.codechicken.org/articles/logging-0.7.0/#using-loguru).

## Install
To install, first download logging information (it executes on Windows) then read the reference work on [[logging.chapter.log](logging.chapter.log)]](http://codeicefacon.org/codeicefacon/logistics/logicle-log598/logmanagement/logging-logging.example.html) and [[logging.chapter.print](logging.chapter.print)]](http://codeicefacon.org/codeicefacon/logistics/logicle-log598/logmanagement/logging-logging.example.html) to know the python logging libraries how to use them.

## What are you waiting for?

A demo version of Loguru has been installed into the Django admin.
Enjoy the demo of Loguru in setting 

* Log to an email on Windows
* Log to a file on Windows
* Log to an email on Unix or Linux
* Log to a file on Unix or Linux
* Log to an URL on Windows
* Log to an email and file on Unix or Linux
* Log to an email and file on Unix or Linux
* Log to a URL on Windows

## How to use Globally

This demo code
```python
from loguru import logger
import os

logger.debug("Saving settings")
settings = {
    "semitest.default": "yes.",
    "semitest.enable": "yes",
    "semitest.append": "enable.",
    "semitest.generator": "echo.",
    "semitest.generator2": "sort ascending, <.txt,.txt-with-times.txt>",
    "semitest.interruption": "yes",
    "semitest.interruption2": [],
    "semitest.cleanup": "yes.",
    "semitest.bottomlevel": "yes",
    "semitest.bottomlevel2": [],
    "semitest.quiet": "yes.",
    "semitest.quiet2": [],
    "semitest.report": "yes",
    "semitest.report2": [],
    "semitest.traceback": "yes.",
    "semitest.traceback2": [],
    "semitest.strict": "yes",
    "semitest.strict2": [],
    "semitest.traceback2.extras": "thunk, traceback, traceback"c,
    "semitest.traceback2.multiples": [],
    "semitest.traceback2.separated": "",
    "semitest.traceback2.suffix": "",
    "semitest.traceback2.yield": "yes",
    "semitest.traceback2.yield2": "",
    "semitest.traceback2.settings": {"w3test.instruments": "yes", "list": ["TOP"]},
    "semitest.tracing.inline": "yes",
    "semitest.tracing.inline2": [],
    "semitest.tracing.pdbdebug": "yes",
    "semitest.tracing.pdb:1",
        "semitest.tr