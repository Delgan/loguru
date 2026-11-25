import multiprocessing
import os
import pickle
import threading

import pytest

from loguru import logger

FORK_AVAILABLE = "fork" in multiprocessing.get_all_start_methods()


def child_log(msg):
    logger.remove()  # this process's core.handlers is now empty
    assert len(logger._core.handlers) == 0
    logger.info(msg)


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_fork_child_forwards(tmp_path):
    logfile = tmp_path / "out.log"
    logger.remove()
    logger.add(logfile, format="{message}", enqueue=True)
    logger.enable_multiprocessing(catch=False)
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


def test_enable_multiprocessing_twice_is_idempotent(tmp_path):
    logger.remove()
    logger.add(tmp_path / "out.log", format="{message}")
    logger.enable_multiprocessing()
    logger.enable_multiprocessing()  # should be a no-op, not start a second manager
    logger.disable_multiprocessing()


def test_disable_multiprocessing_without_enable_is_noop():
    logger.disable_multiprocessing()  # should not raise


def test_listener_reraises_when_catch_false(tmp_path, capfd):
    def broken_sink(msg):
        raise ValueError("boom")

    has_hook = hasattr(threading, "excepthook")
    caught = []

    if has_hook:
        # overwrite whatever pytest's own plugin installed, so our hook runs
        # instead
        original_hook = threading.excepthook

        def record_thread_exception(args):
            caught.append(args.exc_value)

        threading.excepthook = record_thread_exception

    try:
        logger.remove()
        logger.add(broken_sink, catch=False)
        logger.enable_multiprocessing(catch=False)

        ctx = multiprocessing.get_context("spawn")
        p = ctx.Process(target=child_log, args=("trigger",))
        p.start()
        p.join()

        logger.complete()
        logger.disable_multiprocessing()
    finally:
        if has_hook:
            threading.excepthook = original_hook

    if has_hook:
        assert len(caught) == 1
        assert isinstance(caught[0], ValueError)
    else:
        _, err = capfd.readouterr()
        assert "ValueError" in err
        assert "boom" in err


def test_owner_logs_normally_after_enabling(tmp_path):
    logfile = tmp_path / "out.log"
    logger.remove()
    logger.add(logfile, format="{message}")
    logger.enable_multiprocessing()
    logger.info("from the owner itself")  # exercises try_attach's early-return path
    logger.complete()
    logger.disable_multiprocessing()
    assert "from the owner itself" in logfile.read_text()


def test_connect_child_when_owner_unreachable(monkeypatch):
    # simulate stale env vars pointing at nothing
    monkeypatch.setenv("LOGURU_MP_HOST", "127.0.0.1")
    monkeypatch.setenv("LOGURU_MP_PORT", "1")  # nothing listening here
    monkeypatch.setenv("LOGURU_MP_KEY", "00" * 24)
    from loguru import _multiprocessing

    core = logger._core
    core._mp_pending = True
    _multiprocessing.try_attach(core)
    assert core._mp_queue is None  # connect failed silently, as designed


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_disable_multiprocessing_from_forked_child_is_noop(tmp_path):
    logger.remove()
    logger.add(tmp_path / "out.log", format="{message}")
    logger.enable_multiprocessing()

    def child():
        logger.disable_multiprocessing()  # should be a no-op here, not the real owner

    ctx = multiprocessing.get_context("fork")
    p = ctx.Process(target=child)
    p.start()
    p.join()
    assert p.exitcode == 0
    logger.disable_multiprocessing()


def test_try_attach_only_attempts_once():
    from loguru import _multiprocessing

    core = logger._core
    core._mp_pending = True
    core._mp_attempted = True  # simulate an already-attempted core
    _multiprocessing.try_attach(core)  # should return immediately, no attempt made
    assert core._mp_queue is None
    core._mp_attempted = False  # reset so we don't affect other tests


def test_connect_child_without_env_vars_does_nothing(monkeypatch):
    from loguru import _multiprocessing

    monkeypatch.delenv("LOGURU_MP_HOST", raising=False)
    core = logger._core
    _multiprocessing.connect_child(core)
    assert core._mp_queue is None


def test_connect_child_raises_when_owner_unreachable_and_catch_false(monkeypatch):
    from loguru import _multiprocessing

    monkeypatch.setenv("LOGURU_MP_HOST", "127.0.0.1")
    monkeypatch.setenv("LOGURU_MP_PORT", "1")  # nothing listening here
    monkeypatch.setenv("LOGURU_MP_KEY", "00" * 24)
    monkeypatch.setenv("LOGURU_MP_CATCH", "0")  # catch=False
    core = logger._core
    with pytest.raises(OSError, match=r"Connection refused|refused|actively refused"):
        _multiprocessing.connect_child(core)
    assert core._mp_queue is None
