import re

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

with open("loguru/__init__.py", "r") as file:
    regex_version = r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]'
    version = re.search(regex_version, file.read(), re.MULTILINE).group(1)

with open("README.rst", "rb") as file:
    readme = file.read().decode("utf-8")

setup(
    name="loguru",
    version=version,
    packages=["loguru"],
    package_data={"loguru": ["__init__.pyi", "py.typed"]},
    description="Python logging made (stupidly) simple",
    long_description=readme,
    long_description_content_type="text/x-rst",
    author="Delgan",
    author_email="delgan.py@gmail.com",
    url="https://github.com/Delgan/loguru",
    download_url="https://github.com/Delgan/loguru/archive/{}.tar.gz".format(version),
    project_urls={
        "Changelog": "https://github.com/Delgan/loguru/blob/master/CHANGELOG.rst",
        "Documentation": "https://loguru.readthedocs.io/en/stable/index.html",
    },
    keywords=["loguru", "logging", "logger", "log"],
    license="MIT license",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Topic :: System :: Logging",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
    install_requires=[
        "colorama>=0.3.4 ; sys_platform=='win32'",
        "aiocontextvars>=0.2.0 ; python_version<'3.7'",
        "win32-setctime>=1.0.0 ; sys_platform=='win32'",
    ],
    extras_require={
        "dev": [
            # Setup.
            "pre-commit==2.20.0 ; python_version>='3.7'",
            "tox>=3.9.0",
            # Testing framework.
            "pytest>=4.6.2",
            "pytest-cov>=2.7.1",
            "pytest-mypy-plugins>=1.2.0 ; python_version>='3.6'",
            # Testing utils.
            "colorama>=0.3.4",
            "freezegun>=1.1.0",
            "mypy>=v0.910",
            # Docs.
            "Sphinx==5.2.3 ; python_version>='3.6'",
            "sphinx-autobuild==2021.3.14 ; python_version>='3.6'",
            "sphinx-rtd-theme==1.0.0 ; python_version>='3.6'",
            "docutils==0.16 ; python_version>='3.6'",
        ]
    },
    python_requires=">=3.5",
)
