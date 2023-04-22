import multiprocessing
import os
from unittest.mock import MagicMock

import pytest

from loguru import logger


def get_handler_context():
    # No better way to test correct value than to access the private attribute.
    handler = next(iter(logger._core.handlers.values()))
    return handler._multiprocessing_context


def test_default_context():
    logger.add(lambda _: None, context=None)
    assert get_handler_context() == multiprocessing.get_context(None)


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
@pytest.mark.parametrize("context_name", ["fork", "forkserver"])
def test_fork_context_as_string(context_name):
    logger.add(lambda _: None, context=context_name)
    assert get_handler_context() == multiprocessing.get_context(context_name)


def test_spawn_context_as_string():
    logger.add(lambda _: None, context="spawn")
    assert get_handler_context() == multiprocessing.get_context("spawn")


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
@pytest.mark.parametrize("context_name", ["fork", "forkserver"])
def test_fork_context_as_object(context_name):
    context = multiprocessing.get_context(context_name)
    logger.add(lambda _: None, context=context)
    assert get_handler_context() == context


def test_spawn_context_as_object():
    context = multiprocessing.get_context("spawn")
    logger.add(lambda _: None, context=context)
    assert get_handler_context() == context


def test_context_effectively_used():
    default_context = multiprocessing.get_context()
    mocked_context = MagicMock(spec=default_context, wraps=default_context)
    logger.add(lambda _: None, context=mocked_context, enqueue=True)
    logger.complete()
    assert mocked_context.Lock.called


def test_invalid_context_name():
    with pytest.raises(ValueError, match=r"cannot find context for"):
        logger.add(lambda _: None, context="foobar")


@pytest.mark.parametrize("context", [42, object()])
def test_invalid_context_object(context):
    with pytest.raises(
        TypeError,
        match=r"Invalid context, it should be a string or a multiprocessing context",
    ):
        logger.add(lambda _: None, context=context)
