import gc

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
        for generation in range(3):
            gc.collect(generation=generation)


def test_no_deadlock_on_generational_garbage_collection(_remove_cyclic_references):
    """Regression test for https://github.com/Delgan/loguru/issues/712

    Assert that deadlocks do not occur when a cyclic isolate containing log output in
    finalizers is collected by generational GC, during the output of another log message.
    """

    # GIVEN a sink which assigns some memory
    output = []

    def sink(message):
        # This simulates assigning some memory as part of log handling. Eventually this will
        # trigger the generational garbage collector to take over here.
        # You could replace it with `json.dumps(message.record)` to get the same effect.
        _ = [dict() for _ in range(20)]

        # Actually write the message somewhere
        output.append(message)

    logger.add(sink, colorize=False)

    # WHEN there are cyclic isolates in memory which log on GC
    # AND logs are produced long enough to trigger generational GC
    for _ in range(1000):
        CyclicReference()
        logger.info("test")

    # THEN deadlock should not be reached
    assert True
