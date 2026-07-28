import multiprocessing
import time
from loguru import logger
import pickle
import os

def child_log(msg):
    logger.remove()  # this process's core.handlers is now empty
    assert len(logger._core.handlers) == 0
    logger.info(msg)
    
def test_fork_child_forwards(tmp_path):
    logfile = tmp_path / "out.log"
    logger.remove()
    logger.add(logfile, format="{message}", enqueue=True)
    logger.enable_multiprocessing()
    ctx = multiprocessing.get_context("fork")
    p = ctx.Process(target=child_log, args=("hello from child",))
    p.start()
    p.join()
    logger.complete()
    logger.disable_multiprocessing()
    content = logfile.read_text()
    assert "hello from child" in content

def test_spawn_child_forwards(tmp_path):
    logfile = tmp_path / "out.log"
    logger.remove()
    logger.add(logfile, format="{message}", enqueue=True)
    logger.enable_multiprocessing()
    ctx = multiprocessing.get_context("spawn")
    p = ctx.Process(target=child_log, args=("hello from spawned child",))
    p.start()
    p.join()
    logger.complete()
    logger.disable_multiprocessing()
    content = logfile.read_text()
    assert "hello from spawned child" in content

def child_log_n(n):
    logger.remove()
    logger.info("line-{}", n)

def test_multiple_children_all_forward(tmp_path):
    logfile = tmp_path / "out.log"
    logger.remove()
    logger.add(logfile, format="{message}", enqueue=True)
    logger.enable_multiprocessing()
    ctx = multiprocessing.get_context("spawn")
    procs = [ctx.Process(target=child_log_n, args=(i,)) for i in range(10)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    logger.complete()
    logger.disable_multiprocessing()
    lines = logfile.read_text().splitlines()
    expected = {"line-{}".format(i) for i in range(10)}
    assert set(lines) == expected
    assert len(lines) == 10  # nothing dropped, nothing duplicated

def test_not_enabled_child_does_not_forward(tmp_path):
    logfile = tmp_path / "out.log"
    logger.remove()
    logger.add(logfile, format="{message}", enqueue=True)
    # enable_multiprocessing() is intentionally NOT called
    ctx = multiprocessing.get_context("spawn")
    p = ctx.Process(target=child_log, args=("should not appear",))
    p.start()
    p.join()
    logger.complete()
    content = logfile.read_text()
    assert "should not appear" not in content

class NotPicklable:
    def __reduce__(self):
        raise TypeError("nope")


def child_log_bad():
    logger.remove()
    logger.bind(bad=NotPicklable()).info("this should fail to forward")


def test_send_raises_when_catch_false(tmp_path):
    logfile = tmp_path / "out.log"
    logger.remove()
    logger.add(logfile, format="{message}", enqueue=True)
    logger.enable_multiprocessing(catch=False)
    ctx = multiprocessing.get_context("spawn")
    p = ctx.Process(target=child_log_bad)
    p.start()
    p.join()
    logger.complete()
    logger.disable_multiprocessing()
    # the child process should have exited non-zero because send() raised
    assert p.exitcode != 0

def test_pickle_while_multiprocessing_enabled():
    logger.remove()  # no handlers at all, keep this test focused on _mp_* fields only
    logger.enable_multiprocessing()
    dumped = pickle.dumps(logger._core)
    restored = pickle.loads(dumped)
    assert restored._mp_queue is None
    assert restored._mp_pending is False
    assert restored._mp_state is None
    logger.disable_multiprocessing()