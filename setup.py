import os
import re
try:
    from setuptools import setup, Extension
except ImportError:
    from distutils.core import setup, Extension

with open('loguru/__init__.py', 'r') as file:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        file.read(), re.MULTILINE).group(1)

with open('README.rst', 'rb') as file:
    readme = file.read().decode('utf-8')

LOGURU_EXTENSIONS = os.getenv("LOGURU_EXTENSIONS", None)

if LOGURU_EXTENSIONS == "0":
    ext_modules = []
else:
    optional = LOGURU_EXTENSIONS != "1"
    ext_modules = [
        Extension('loguru._extensions.fast_now', sources=['loguru/_extensions/fast_now.c'], optional=optional),
    ]

setup(
    name='loguru',
    version=version,
    description='Python logging made (stupidly) simple',
    long_description=readme,
    author='Delgan',
    author_email='delgan.py@gmail.com',
    url='https://github.com/Delgan/loguru',
    download_url='https://github.com/Delgan/loguru/archive/{}.tar.gz'.format(version),
    keywords=['loguru', 'logging', 'logger', 'log'],
    license="MIT license",
    install_requires=[
        'ansimarkup>=1.3.0',
        'base36>=0.1.1',
        'better_exceptions_fork>=0.2.1.post5',
        'colorama>=0.3.9',
        'pendulum>=1.4.2',
    ],
    extras_require={
        'dev': [
            'coveralls>=1.3.0',
            'pytest>=3.5.0',
            'pytest-benchmark>=3.1.1',
            'pytest-cov>=2.5.1',
        ],
    },
    ext_modules=ext_modules,
)
