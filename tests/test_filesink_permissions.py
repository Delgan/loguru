import pytest
import os
from stat import S_IMODE
import re
import sys
import time
from loguru import logger


@pytest.mark.parametrize("permissions", [None, 0o0777, 0o0766, 0o0744])
def test_log_file_permissions(tmpdir, permissions):
    log_file_name = "file.log"
    logger.add(str(tmpdir.join(log_file_name)), file_permissions=permissions, format="{message}")

    time.sleep(0.1)
    logger.debug("a")

    files = sorted(tmpdir.listdir())
    assert len(files) == 1

    assert files[0].basename == "file.log"
    assert files[0].read() == "a\n"

    if permissions and "win" not in sys.platform:
        st = os.stat(str(files[0]))
        oct_perm = oct(S_IMODE(st.st_mode))
        assert oct_perm == oct(permissions)


@pytest.mark.parametrize("permissions", [None, 0o0777, 0o0766, 0o0744])
def test_rotation_permissions(tmpdir, permissions):
    logger.add(str(tmpdir.join("file.log")), rotation=0, file_permissions=permissions, format="{message}")

    time.sleep(0.1)
    logger.debug("a")

    files = sorted(tmpdir.listdir())
    assert len(files) == 2
    assert re.match(r"file\.[0-9-_]+\.log", files[0].basename)
    assert files[1].basename == "file.log"
    assert files[0].read() == ""
    assert files[1].read() == "a\n"
    if permissions and "win" not in sys.platform:
        for f in files:
            st = os.stat(str(f))
            oct_perm = oct(S_IMODE(st.st_mode))
            assert oct_perm == oct(permissions)

    time.sleep(0.1)
    logger.debug("b")

    files = sorted(tmpdir.listdir())
    assert len(files) == 3
    assert all(re.match(r"file\.[0-9-_]+\.log", f.basename) for f in files[:2])
    if permissions and "win" not in sys.platform:
        for f in files:
            st = os.stat(f)
            oct_perm = oct(S_IMODE(st.st_mode))
            assert oct_perm == oct(permissions)

