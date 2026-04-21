import sys

import pytest

try:
    mypy_api = None  # type: Optional[ModuleType]
    import mypy.api as mypy_api  # noqa: F811
except ImportError:
    pass


@pytest.mark.skipif(mypy_api is None, reason="Requires mypy to be installed.")
def test_mypy_import():
    # Check stub file is valid and can be imported by Mypy.
    # There exist others tests in "typesafety" subfolder but they require a recent Python version.
    out, _, result = mypy_api.run(["--strict", "-c", "from loguru import logger"])
    print("".join(out), file=sys.stderr)
    assert result == 0
