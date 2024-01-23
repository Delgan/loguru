import multiprocessing
import os

import pytest

from loguru import logger


@pytest.fixture
def fork_context():
    yield multiprocessing.get_context("fork")


@pytest.fixture
def spawn_context():
    yield multiprocessing.get_context("spawn")


class Writer:
    def __init__(self):
        self._output = ""

    def write(self, message):
        self._output += message

    def read(self):
        return self._output


def subworker(logger):
    logger.reinstall()
    logger.info("Child")
    deeper_subworker()


def deeper_subworker():
    logger.info("Grandchild")


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_process_fork(fork_context):
    writer = Writer()

    logger.add(writer, context=fork_context, format="{message}", enqueue=True, catch=False)

    process = fork_context.Process(target=subworker, args=(logger,))
    process.start()
    process.join()

    assert process.exitcode == 0

    logger.info("Main")
    logger.remove()

    assert writer.read() == "Child\nGrandchild\nMain\n"


def test_process_spawn(spawn_context):
    writer = Writer()

    logger.add(writer, context=spawn_context, format="{message}", enqueue=True, catch=False)

    process = spawn_context.Process(target=subworker, args=(logger,))
    process.start()
    process.join()

    assert process.exitcode == 0

    logger.info("Main")
    logger.remove()

    assert writer.read() == "Child\nGrandchild\nMain\n"
