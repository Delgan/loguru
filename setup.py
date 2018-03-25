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

setup(
    name = 'loguru',
    version = version,
    description = 'Python logging made (stupidly) simple',
    long_description = readme,
    author = 'Delgan',
    author_email = 'delgan.py@gmail.com',
    url = 'https://github.com/Delgan/loguru',
    download_url = 'https://github.com/Delgan/loguru/archive/{}.tar.gz'.format(version),
    keywords = ['loguru', 'logging', 'logger', 'log'],
    license="MIT license",
    classifiers = [],
    install_requires = [
        'ansimarkup>=1.3.0',
        'base36>=0.1.1',
        'better_exceptions_fork>=0.2.1.post5',
        'colorama>=0.3.9',
        'pendulum>=1.4.2',
    ],
    ext_modules = [
        Extension('loguru._extensions.fast_now', sources=['loguru/_extensions/fast_now.c'], optional=True)
    ]
)
