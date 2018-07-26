from unittest.mock import MagicMock
from loguru import notifier, logger
import pytest


def test_notifier_directly():
    noti = notifier.email(to="dest@gmail.com")
    mock = MagicMock()
    noti.provider.notify = mock
    noti.notify("Test")
    assert mock.call_count == 1

def test_notifier_as_sink():
    noti = notifier.email(to="dest@gmail.com")
    mock = MagicMock()
    noti.provider.notify = mock
    logger.start(noti.notify)
    logger.info("Test")
    assert mock.call_count == 1
