import os
import sys
import multiprocessing
import loguru
from loguru import logger
import time
import pytest


def do_something(i):
    logger.info("#{}", i)


def set_logger(logger_):
    global logger
    logger = logger_


def subworker(logger_):
    logger_.info("Child")


def subworker_inheritance():
    logger.info("Child")


def subworker_remove(logger_):
    logger_.info("Child")
    logger_.remove()
    logger_.info("Nope")


def subworker_remove_inheritance():
    logger.info("Child")
    logger.remove()
    logger.info("Nope")


def subworker_barrier(logger_, barrier):
    logger_.info("Child")
    barrier.wait()
    time.sleep(0.5)
    logger_.info("Nope")


def subworker_barrier_inheritance(barrier):
    logger.info("Child")
    barrier.wait()
    time.sleep(0.5)
    logger.info("Nope")


class Writer:
    def __init__(self):
        self._output = ""

    def write(self, message):
        self._output += message

    def read(self):
        return self._output


def test_apply_spawn(monkeypatch):
    ctx = multiprocessing.get_context("spawn")
    monkeypatch.setattr(loguru._handler, "multiprocessing", ctx)

    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True)

    with ctx.Pool(1, set_logger, [logger]) as pool:
        for i in range(3):
            pool.apply(do_something, (i,))
        pool.close()
        pool.join()

    logger.info("Done!")
    logger.remove()

    assert writer.read() == "#0\n#1\n#2\nDone!\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_apply_fork():
    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True)

    with multiprocessing.Pool(1, set_logger, [logger]) as pool:
        for i in range(3):
            pool.apply(do_something, (i,))
        pool.close()
        pool.join()

    logger.info("Done!")
    logger.remove()

    assert writer.read() == "#0\n#1\n#2\nDone!\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_apply_inheritance():
    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True)

    with multiprocessing.Pool(1) as pool:
        for i in range(3):
            pool.apply(do_something, (i,))
        pool.close()
        pool.join()

    logger.info("Done!")
    logger.remove()

    assert writer.read() == "#0\n#1\n#2\nDone!\n"


def test_apply_async_spawn(monkeypatch):
    ctx = multiprocessing.get_context("spawn")
    monkeypatch.setattr(loguru._handler, "multiprocessing", ctx)

    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True)

    with ctx.Pool(1, set_logger, [logger]) as pool:
        for i in range(3):
            result = pool.apply_async(do_something, (i,))
            result.get()
        pool.close()
        pool.join()

    logger.info("Done!")
    logger.remove()

    assert writer.read() == "#0\n#1\n#2\nDone!\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_apply_async_fork():
    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True)

    with multiprocessing.Pool(1, set_logger, [logger]) as pool:
        for i in range(3):
            result = pool.apply_async(do_something, (i,))
            result.get()
        pool.close()
        pool.join()

    logger.info("Done!")
    logger.remove()

    assert writer.read() == "#0\n#1\n#2\nDone!\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_apply_async_inheritance():
    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True)

    with multiprocessing.Pool(1) as pool:
        for i in range(3):
            result = pool.apply_async(do_something, (i,))
            result.get()
        pool.close()
        pool.join()

    logger.info("Done!")
    logger.remove()

    assert writer.read() == "#0\n#1\n#2\nDone!\n"


def test_process_spawn(monkeypatch):
    ctx = multiprocessing.get_context("spawn")
    monkeypatch.setattr(loguru._handler, "multiprocessing", ctx)

    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True)

    process = ctx.Process(target=subworker, args=(logger,))
    process.start()
    process.join()

    logger.info("Main")
    logger.remove()

    assert writer.read() == "Child\nMain\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_process_fork():
    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True)

    process = multiprocessing.Process(target=subworker, args=(logger,))
    process.start()
    process.join()

    logger.info("Main")
    logger.remove()

    assert writer.read() == "Child\nMain\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_process_inheritance():
    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True)

    process = multiprocessing.Process(target=subworker_inheritance)
    process.start()
    process.join()

    logger.info("Main")
    logger.remove()

    assert writer.read() == "Child\nMain\n"


def test_remove_in_child_process_spawn(monkeypatch):
    ctx = multiprocessing.get_context("spawn")
    monkeypatch.setattr(loguru._handler, "multiprocessing", ctx)

    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True)

    process = ctx.Process(target=subworker_remove, args=(logger,))
    process.start()
    process.join()

    logger.info("Main")
    logger.remove()

    assert writer.read() == "Child\nMain\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_remove_in_child_process_fork():
    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True)

    process = multiprocessing.Process(target=subworker_remove, args=(logger,))
    process.start()
    process.join()

    logger.info("Main")
    logger.remove()

    assert writer.read() == "Child\nMain\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_remove_in_child_process_inheritance():
    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True)

    process = multiprocessing.Process(target=subworker_remove_inheritance)
    process.start()
    process.join()

    logger.info("Main")
    logger.remove()

    assert writer.read() == "Child\nMain\n"


def test_remove_in_main_process_spawn(monkeypatch):
    # Actually, this test may fail if sleep time in main process is too small (and no barrier used)
    # In such situation, it seems the child process has not enough time to initialize itself
    # It may fail with an "EOFError" during unpickling of the (garbage collected / closed) Queue
    ctx = multiprocessing.get_context("spawn")
    monkeypatch.setattr(loguru._handler, "multiprocessing", ctx)

    writer = Writer()
    barrier = ctx.Barrier(2)

    logger.add(writer, format="{message}", enqueue=True)

    process = ctx.Process(target=subworker_barrier, args=(logger, barrier))
    process.start()
    barrier.wait()
    logger.info("Main")
    logger.remove()
    process.join()

    assert writer.read() == "Child\nMain\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_remove_in_main_process_fork():
    writer = Writer()
    barrier = multiprocessing.Barrier(2)

    logger.add(writer, format="{message}", enqueue=True)

    process = multiprocessing.Process(target=subworker_barrier, args=(logger, barrier))
    process.start()
    barrier.wait()
    logger.info("Main")
    logger.remove()
    process.join()

    assert writer.read() == "Child\nMain\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_remove_in_main_process_inheritance():
    writer = Writer()
    barrier = multiprocessing.Barrier(2)

    logger.add(writer, format="{message}", enqueue=True)

    process = multiprocessing.Process(target=subworker_barrier_inheritance, args=(barrier,))
    process.start()
    barrier.wait()
    logger.info("Main")
    logger.remove()
    process.join()

    assert writer.read() == "Child\nMain\n"


def test_not_picklable_sinks_spawn(monkeypatch, tmpdir, capsys):
    ctx = multiprocessing.get_context("spawn")
    monkeypatch.setattr(loguru._handler, "multiprocessing", ctx)

    filepath = tmpdir.join("test.log")
    stream = sys.stderr
    output = []

    logger.add(str(filepath), format="{message}", enqueue=True)
    logger.add(stream, format="{message}", enqueue=True)
    logger.add(lambda m: output.append(m), format="{message}", enqueue=True)

    process = ctx.Process(target=subworker, args=[logger])
    process.start()
    process.join()

    logger.info("Main")
    logger.remove()

    out, err = capsys.readouterr()

    assert filepath.read() == "Child\nMain\n"
    assert out == ""
    assert err == "Child\nMain\n"
    assert output == ["Child\n", "Main\n"]


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_not_picklable_sinks_fork(capsys, tmpdir):
    filepath = tmpdir.join("test.log")
    stream = sys.stderr
    output = []

    logger.add(str(filepath), format="{message}", enqueue=True)
    logger.add(stream, format="{message}", enqueue=True)
    logger.add(lambda m: output.append(m), format="{message}", enqueue=True)

    process = multiprocessing.Process(target=subworker, args=[logger])
    process.start()
    process.join()

    logger.info("Main")
    logger.remove()

    out, err = capsys.readouterr()

    assert filepath.read() == "Child\nMain\n"
    assert out == ""
    assert err == "Child\nMain\n"
    assert output == ["Child\n", "Main\n"]


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_not_picklable_sinks_inheritance(capsys, tmpdir):
    filepath = tmpdir.join("test.log")
    stream = sys.stderr
    output = []

    logger.add(str(filepath), format="{message}", enqueue=True)
    logger.add(stream, format="{message}", enqueue=True)
    logger.add(lambda m: output.append(m), format="{message}", enqueue=True)

    process = multiprocessing.Process(target=subworker_inheritance)
    process.start()
    process.join()

    logger.info("Main")
    logger.remove()

    out, err = capsys.readouterr()

    assert filepath.read() == "Child\nMain\n"
    assert out == ""
    assert err == "Child\nMain\n"
    assert output == ["Child\n", "Main\n"]
