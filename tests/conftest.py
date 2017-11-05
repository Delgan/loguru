import loguru
import pytest

@pytest.fixture
def logger():
    return loguru.Logger()

@pytest.fixture
def writer():

    def w(message):
        w.written.append(message)

    w.written = []
    w.read = lambda: ''.join(w.written)
    w.clear = lambda: w.written.clear()

    return w
