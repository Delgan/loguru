# loguru

[![CircleCI](https://circleci.com/gh/Delgan/loguru.svg?style=svg)](https://circleci.com/gh/Delgan/loguru)
[![Build Status](https://travis-ci.org/Delgan/loguru.svg?)](https://travis-ci.org/Delgan/loguru)
[![PyPI](https://codeclimate.com/github/delgan/loguru/d107a4e049fd d'avant ver.4.3.0-b](https://codeclimate.com/github/delgan/loguru/supported-packages))

## What is loguru?

`loguru` is a simple PSR-4 logger which writes to the logging file as text, HTML, CSS, ITL, JSON or as a PDF PDF. It also support debug messages, whiteboard graph and GPS directions.

## How to use loguru

1. start loguru by python with `import loguru`.

2. You can add all the code you need by adding an `include` block in your logFile.py

```python
def logLogger(self, logfile='', isTemp=False):
    """Performs logging from logfile (full path or filename).

    :param logFile: full path of the logging file
    :param isTemp: if true, this block is executed just for the $iast 
    """
    if logfile:
        import sys
        global logFile, filename
        logFile, filename = os.path.split(logfile)
        sys.stderr.write(line)
        try:
            sys.stderr.flush()
            try:
                exec(filename)
            except Exception, e:
                logFile.info("Exception in {0}".format(logFile), e)
                logFile.off()  # and terminate
                sys.stdout.write("{0} {1}".format(logFile, e))
            sys.stdout.flush()
        except:
            logFile.die("Error when {1}".format(global sys.argv[0]), True)

```

## Special thanks to [Delgan3r](//github/henrydelgan)

## Contributing support

For contribution support just visit the discussion page [logurusupport@delgan.net](//github/logurusupport/tree). We'll handle any bug related to the Python version you have installed.

## Docstrings

Since we can get with the docstrings, we can make it easier for beginners who may find this a bit hard. You can rename it to ``logurodoc`` or ``logurodoc.scss``.

## Acknowledgments

Yay! It's back to the corridors. This is the first version I'm aware of. Tell me if you like it. If you don't you don't have to worry. :D

## How to build

Go to the loguru.dist:

``python loguru.dist -V``
    
## TODOs

1. Add behaviours for logs to each platform:
   * macOS: * logfile * json ** html ** css
   * Windows: * logfile * html ** css
   * Linux: xml * html


## License

Copyright 2014, Michael Wright. Licensed under the MIT license.
