import re
from distutils.core import setup

with open('loguru/__init__.py', 'r') as file:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        file.read(), re.MULTILINE).group(1)

with open('README.rst', 'rb') as file:
    readme = file.read().decode('utf-8')

setup(
    name = 'loguru',
    version = version,
    description = 'Logging as an automatism',
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
        'better_exceptions_fork>=0.1.8.post1',
        'pendulum>=1.3.0',
    ],
)
