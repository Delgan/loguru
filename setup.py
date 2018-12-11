import os
import re

try:
    from setuptools import setup, Extension
except ImportError:
    from distutils.core import setup, Extension

HERE = lambda file_path: os.path.join(os.path.dirname(__file__), file_path)

with open(HERE("loguru/__init__.py"), "r") as file:
    regex_version = r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]'
    version = re.search(regex_version, file.read(), re.MULTILINE).group(1)

with open(HERE("README.rst"), "rb") as file:
    readme = file.read().decode("utf-8")


def install():
    setup(
        name="loguru",
        version=version,
        packages=["loguru"],
        description="Python logging made (stupidly) simple",
        long_description=readme,
        author="Delgan",
        author_email="delgan.py@gmail.com",
        url="https://github.com/Delgan/loguru",
        download_url=f"https://github.com/Delgan/loguru/archive/{version}.tar.gz",
        keywords=["loguru", "logging", "logger", "log", "parser"],
        license="MIT license",
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Intended Audience :: Developers",
            "Natural Language :: English",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: Implementation :: CPython",
        ],
        install_requires=[
            "ansimarkup>=1.4.0",
            "better_exceptions_fork>=0.2.1.post6",
            "colorama>=0.4.1",
        ],
        extras_require={
            "dev": [
                "black>=18.6b4",
                "coveralls>=1.3.0",
                "isort>=4.3.4",
                "pytest>=3.5.0",
                "pytest-cov>=2.5.1",
                "Sphinx>=1.7.4",
                "sphinx-autobuild>=0.7",
                "sphinx-rtd-theme>=0.3",
            ]
        },
        python_requires=">=3.6",
    )


if __name__ == '__main__':
    install()
