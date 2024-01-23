import multiprocessing
import os
from unittest.mock import patch

import pytest

from loguru import logger


@pytest.fixture
def reset_start_method():
    yield
    multiprocessing.set_start_method(None, force=True)


@pytest.mark.usefixtures("reset_start_method")
def test_using_multiprocessing_directly_if_context_is_none():
    logger.add(lambda _: None, enqueue=True, context=None)
    assert multiprocessing.get_start_method(allow_none=True) is not None


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
@pytest.mark.parametrize("context_name", ["fork", "forkserver"])
def test_fork_context_as_string(context_name):
    context = multiprocessing.get_context(context_name)
    with patch.object(type(context), "Lock", wraps=context.Lock) as mock:
        logger.add(lambda _: None, context=context_name, enqueue=True)
        assert mock.called
    assert multiprocessing.get_start_method(allow_none=True) is None


def test_spawn_context_as_string():
    context = multiprocessing.get_context("spawn")
    with patch.object(type(context), "Lock", wraps=context.Lock) as mock:
        logger.add(lambda _: None, context="spawn", enqueue=True)
        assert mock.called
    assert multiprocessing.get_start_method(allow_none=True) is None


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
@pytest.mark.parametrize("context_name", ["fork", "forkserver"])
def test_fork_context_as_object(context_name):
    context = multiprocessing.get_context(context_name)
    with patch.object(type(context), "Lock", wraps=context.Lock) as mock:
        logger.add(lambda _: None, context=context, enqueue=True)
        assert mock.called
    assert multiprocessing.get_start_method(allow_none=True) is None


def test_spawn_context_as_object():
    context = multiprocessing.get_context("spawn")
    with patch.object(type(context), "Lock", wraps=context.Lock) as mock:
        logger.add(lambda _: None, context=context, enqueue=True)
        assert mock.called
    assert multiprocessing.get_start_method(allow_none=True) is None


def test_global_start_method_is_none_if_enqueue_is_false():
    logger.add(lambda _: None, enqueue=False, context=None)
    assert multiprocessing.get_start_method(allow_none=True) is None


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
