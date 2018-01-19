import pendulum
import loguru
import pytest
import sys
from unittest.mock import MagicMock

@pytest.mark.parametrize('with_extensions', [True, False])
def test_get_fast_now_function(monkeypatch, with_extensions):
    if with_extensions:
        monkeypatch.setitem(sys.modules, 'loguru._extensions.fast_now', MagicMock())
    else:
        monkeypatch.setitem(sys.modules, 'loguru._extensions.fast_now', MagicMock(spec_set=[]))

    fast_now = loguru._fast_now.get_fast_now_function()
    assert isinstance(fast_now(), pendulum.Pendulum)

def test_fast_now():
    now_1 = loguru._fast_now.fast_now()
    assert isinstance(now_1, pendulum.Pendulum)

    now_2 = loguru._fast_now.fast_now()
    assert now_2 >= now_1
