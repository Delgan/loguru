import gc
import pickle
import sys
import threading
import time

import pytest

from loguru import logger


class CyclicReference:
    """A minimal cyclic reference.

    Cyclical references are garbage collected using the generational collector rather than
    via reference counting. This is important here, because the generational collector runs
    periodically, meaning that it is hard to predict when the stack will be overtaken by a
    garbage collection process - but it will almost always be when allocating memory of some
    kind.

    When this object is garbage-collected, a log will be emitted.
    """

    def __init__(self, _other: "CyclicReference" = None):
        self.other = _other or CyclicReference(_other=self)

    def __del__(self):
        logger.info("tearing down")


@pytest.fixture()
def _remove_cyclic_references():
    """Prevent cyclic isolate finalizers bleeding into other tests."""
    try:
        yield
    finally:
        gc.collect()


def test_no_deadlock_on_generational_garbage_collection(_remove_cyclic_references):
    """Regression test for https://github.com/Delgan/loguru/issues/712

    Assert that deadlocks do not occur when a cyclic isolate containing log output in
    finalizers is collected by generational GC, during the output of another log message.
    """

    # GIVEN a sink which assigns some memory
    output = []

    def sink(message):
        # The generational GC could be triggered here by any memory assignment, but we
        # trigger it explicitly to avoid a flaky test.
        # See https://github.com/Delgan/loguru/issues/712
        gc.collect()

        # Actually write the message somewhere
        output.append(message)

    logger.add(sink, colorize=False)

    # WHEN there are cyclic isolates in memory which log on GC
    # AND logs are produced long enough to trigger generational GC
    for _ in range(10):
        CyclicReference()
        logger.info("test")

    # THEN deadlock should not be reached
    assert True


def test_no_deadlock_if_logger_used_inside_sink_with_catch(capsys):
    def sink(message):
        logger.info(message)

    logger.add(sink, colorize=False, catch=True)

    logger.info("Test")

    out, err = capsys.readouterr()
    assert out == ""
    assert "deadlock avoided" in err


def test_no_deadlock_if_logger_used_inside_sink_without_catch():
    def sink(message):
        logger.info(message)

    logger.add(sink, colorize=False, catch=False)

    with pytest.raises(RuntimeError, match=r".*deadlock avoided.*"):
        logger.info("Test")


def test_no_error_if_multithreading(capsys):
    barrier = threading.Barrier(2)

    def sink(message):
        barrier.wait()
        sys.stderr.write(message)
        time.sleep(0.5)  # Give time to the other thread to try to acquire the lock.

    def worker():
        logger.info("Thread message")
        barrier.wait()  # Release main thread.

    logger.add(sink, colorize=False, catch=False, format="{message}")
    thread = threading.Thread(target=worker)
    thread.start()

    barrier.wait()
    logger.info("Main message")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == "Thread message\nMain message\n"


def _pickle_sink(message):
    sys.stderr.write(message)

    if message.record["extra"].get("clone", False):
        new_logger = pickle.loads(pickle.dumps(logger))
        new_logger.bind(clone=False).info("From clone")


def test_pickled_logger_does_not_inherit_acquired_local(capsys):
    logger.add(_pickle_sink, colorize=False, catch=False, format="{message}")

    logger.bind(clone=True).info("From main")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == "From main\nFrom clone\n"
