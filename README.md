# loguru
[![Build Status](https://travis-ci.org/delaran/loguru.svg?branch=master)](https://travis-ci.org/delgan/loguru)


Loguru is a logging framework based upon the [django project](http://django.org/).

## Dependencies

* [Sphinx](https://github.com/Sphinx-Sphinx/sphinx)

## Installation

[re.python](https://github.com/re-python/re.python) is required to install this library. It installs it with pip.
This means you first need to install [re.python](https://travis-ci.org/delgan/re.python) before
installing loguru. There are more than one way to meet requirement. However, this is the two easiest:

1. Clone repository: `git clone https://github.com/delan/loguru.git`
2. Install package: `pip install re.python`

## Usage

Use logger inside your app. You are free to call other logger without any module dependencies:

```python
def log(level, message, __context = None):
   logger.debug(message)
```

Or also call inside context:

```python
from loguru import VideoLog

video_log = VideoLog()


print video_log.get_playback_result()

```

You should take these settings of your logger:
```python
log_level = logging.DEBUG
log_message = 'DEBUG, youtube'
log_message_first_level = 'DEBUG, youtube'
logger               = logging.getLogger()
logger.addHandler(handler)
           
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger().setLevel(logging.DEBUG)

```

The **logging.Messages** can be also configured before:

```python
logging.info('Information')
logging.debug('Debug')
logging.info('Instruction')
logging.warning('Warning')
```

## Setting Default Configuration

#### Logger limits

You can set a maximum of *log_level* logging levels. Example is **logging.INFO**, **logging.DEBUG** or **logging.WARNING**.

re.data_path is the base path where all the files reside. You can use a different path for logging:

```python
re.data_path = 'c:\\Inventory\\Log'
```

login_dir is the base path where the login database is stored. To configure different login paths use
different database path (if any).

**Logging** is the class which extends the **sphinx.ext.i18n.web.sphinx_defaults** module:

Run your template with `loguru.sphinx.extensions.sphinx_defaultstemplate` which was just installed:

```python
modname="Loguru"

w = logging.getLogger()


def must_passe(*args, **kwargs):
    webinit = json.loads(data)

    ## Check for Cookie
    w.config['cookie_secure'] = webinit['secure']
    w.config['cookie_username'] = webinit['username']
    w.config['cookie