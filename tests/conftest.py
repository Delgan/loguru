import loguru
import pytest
import py
import os

@pytest.fixture
def logger():
    return loguru._logger.Logger()

@pytest.fixture
def writer():

    def w(message):
        w.written.append(message)

    w.written = []
    w.read = lambda: ''.join(w.written)
    w.clear = lambda: w.written.clear()

    return w

@pytest.fixture
def pyexec(tmpdir):
    file = tmpdir.join("test.py")
    loguru_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    loguru_config = ('import sys;'
                     'sys.path.append("' + loguru_path + '");'
                     'from loguru import logger;'
                     'logger.stop();\n')

    def pyexec(code, import_loguru=False, *, pyfile=None):
        if import_loguru:
            code = loguru_config + code
        else:
            code = "# padding\n" + code

        if pyfile is None:
            pyfile = file
        pyfile.write(code)
        out = py.process.cmdexec('python %s' % pyfile.realpath())
        return out

    return pyexec

@pytest.fixture
def monkeypatch_now(monkeypatch):

    def monkeypatch_now(func):
        monkeypatch.setattr(loguru._logger, 'pendulum_now', func)
        monkeypatch.setattr(loguru._file_sink, 'pendulum_now', func)

    return monkeypatch_now
