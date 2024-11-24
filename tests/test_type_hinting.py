import sys

import mypy.api


def test_mypy_import():
    # Check stub file is valid and can be imported by Mypy.
    # There exist others tests in "typesafety" subfolder but they aren't compatible with Python 3.5.
    out, _, result = mypy.api.run(["--strict", "-c", "from loguru import logger"])
    print("".join(out), file=sys.stderr)
    assert result == 0
