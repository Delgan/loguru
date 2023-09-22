import mypy.api


def test_mypy_import():
    # Check stub file is valid and can be imported by Mypy.
    # There exist others tests in "typesafety" subfolder but they aren't compatible with Python 3.5.
    _, _, result = mypy.api.run(["--strict", "-c", "from loguru import logger"])
    assert result == 0
