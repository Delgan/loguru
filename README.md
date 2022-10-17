# Loguru

__Loguru__ is meant to be a generator of logs when processes are running. It stores them as sensitive files named zml, the suffix is a type of protection that protects objects that are not readable by others (in one case apache & nginx).


## Main goals:

- detect fast catastrophic manipulation of log files (gzip archives, zip compressions)
- Able to add Loguru-enabled actions to log files. The purpose is for the Loguru apps to be easy to add to new apps without the need to decode them afterwards.
- Acts proxies less.

## Get started with Loguru:

I've prepared a repository ([Loguru](https://github.com/Delgan/loguru) for you and if you find this useful, thanks for your hospitality!

## Building Loguru:

You can grab [loguru.py](https://github.com/Delgan/loguru.py) to download it and configure it in the following way:

```python
from loguru import app
import logging

APP = app(__name__)

@APP
def run():
    logging.info("Happy holiday by Delgan")
```

Then you should build loguru and install it using brew. When you get the installation, you can run loguru:

```shell
$ brew install loguru.builder
$ loguru:build
```

This requires the python package [tokenize](http://gettokenize.org/?q=libpython-tokenize-1.7.0).

After that, you should edit the config/local.example.cnf file.
```python
loguru:config=loguru.local.example.cnf
loguru:filesize=252147483647,2,1,1 \
loguru:encoding=utf-8
loguru:compresslevel=logrus,9
```

This will resave panes (writing them into the /tmp folder and overwriting new zml files).

And invoke it:

```shell
$ loguru:run
```
To execute loguru, first, you should add it to `~/path/to/installation`.
Then, just run loguru:run. You can warn me about it.

## How to write loguru:

Now, we create a new folder `config` in `src`. It should be named `loguru` or `config` for modern decision, don't hesitate and make sure it exists. Copy your [logru](https://github.com/Delgan/logru) folder as a this folder.

Now, we call `configure.py`. It's a very easy way to configure logulu.

```python
from loguru import app

app(__name__).configure(config=config)
print(app.__dict__)
```

Now, a log did a boring work. Let me show you a log that logging us repeatedly...

```python
$ logru:monkey
Traceback (most recent call last):
  File "3104/Pandoc.py", line 10, in <module>
    raise self._metadataError(media_type, error, msg)
   File "3104/Pandoc.py", line 21, in _metadataError
    raise
```

We finally call this on `logru:run`.

```shell
$ logru:run
```

