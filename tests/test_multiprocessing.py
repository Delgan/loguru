import asyncio
import copy
import os
import platform
import sys
import threading
import time

import pytest

import loguru
from loguru import logger


@pytest.fixture
def fork_context(monkeypatch):
    import multiprocessing

    context = multiprocessing.get_context("fork")
    monkeypatch.setattr(loguru._handler, "multiprocessing", context)
    yield context


@pytest.fixture
def spawn_context(monkeypatch):
    import multiprocessing

    context = multiprocessing.get_context("spawn")
    monkeypatch.setattr(loguru._handler, "multiprocessing", context)
    yield context


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


def subworker_complete(logger_):
    async def work():
        logger_.info("Child")
        await logger_.complete()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(work())


def subworker_complete_inheritance():
    async def work():
        logger.info("Child")
        await logger.complete()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(work())


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


@pytest.mark.skipif(platform.python_implementation() == "PyPy", reason="PyPy bug #3630")
def test_apply_spawn(spawn_context):
    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True, catch=False)

    with spawn_context.Pool(1, set_logger, [logger]) as pool:
        for i in range(3):
            pool.apply(do_something, (i,))
        pool.close()
        pool.join()

    logger.info("Done!")
    logger.remove()

    assert writer.read() == "#0\n#1\n#2\nDone!\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_apply_fork(fork_context):
    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True, catch=False)

    with fork_context.Pool(1, set_logger, [logger]) as pool:
        for i in range(3):
            pool.apply(do_something, (i,))
        pool.close()
        pool.join()

    logger.info("Done!")
    logger.remove()

    assert writer.read() == "#0\n#1\n#2\nDone!\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_apply_inheritance(fork_context):
    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True, catch=False)

    with fork_context.Pool(1) as pool:
        for i in range(3):
            pool.apply(do_something, (i,))
        pool.close()
        pool.join()

    logger.info("Done!")
    logger.remove()

    assert writer.read() == "#0\n#1\n#2\nDone!\n"


@pytest.mark.skipif(platform.python_implementation() == "PyPy", reason="PyPy bug #3630")
def test_apply_async_spawn(spawn_context):
    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True, catch=False)

    with spawn_context.Pool(1, set_logger, [logger]) as pool:
        for i in range(3):
            result = pool.apply_async(do_something, (i,))
            result.get()
        pool.close()
        pool.join()

    logger.info("Done!")
    logger.remove()

    assert writer.read() == "#0\n#1\n#2\nDone!\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_apply_async_fork(fork_context):
    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True, catch=False)

    with fork_context.Pool(1, set_logger, [logger]) as pool:
        for i in range(3):
            result = pool.apply_async(do_something, (i,))
            result.get()
        pool.close()
        pool.join()

    logger.info("Done!")
    logger.remove()

    assert writer.read() == "#0\n#1\n#2\nDone!\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_apply_async_inheritance(fork_context):
    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True, catch=False)

    with fork_context.Pool(1) as pool:
        for i in range(3):
            result = pool.apply_async(do_something, (i,))
            result.get()
        pool.close()
        pool.join()

    logger.info("Done!")
    logger.remove()

    assert writer.read() == "#0\n#1\n#2\nDone!\n"


@pytest.mark.skipif(platform.python_implementation() == "PyPy", reason="PyPy bug #3630")
def test_process_spawn(spawn_context):
    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True, catch=False)

    process = spawn_context.Process(target=subworker, args=(logger,))
    process.start()
    process.join()

    assert process.exitcode == 0

    logger.info("Main")
    logger.remove()

    assert writer.read() == "Child\nMain\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_process_fork(fork_context):
    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True, catch=False)

    process = fork_context.Process(target=subworker, args=(logger,))
    process.start()
    process.join()

    assert process.exitcode == 0

    logger.info("Main")
    logger.remove()

    assert writer.read() == "Child\nMain\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_process_inheritance(fork_context):
    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True, catch=False)

    process = fork_context.Process(target=subworker_inheritance)
    process.start()
    process.join()

    assert process.exitcode == 0

    logger.info("Main")
    logger.remove()

    assert writer.read() == "Child\nMain\n"


@pytest.mark.skipif(platform.python_implementation() == "PyPy", reason="PyPy bug #3630")
def test_remove_in_child_process_spawn(spawn_context):
    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True, catch=False)

    process = spawn_context.Process(target=subworker_remove, args=(logger,))
    process.start()
    process.join()

    assert process.exitcode == 0

    logger.info("Main")
    logger.remove()

    assert writer.read() == "Child\nMain\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_remove_in_child_process_fork(fork_context):
    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True, catch=False)

    process = fork_context.Process(target=subworker_remove, args=(logger,))
    process.start()
    process.join()

    assert process.exitcode == 0

    logger.info("Main")
    logger.remove()

    assert writer.read() == "Child\nMain\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_remove_in_child_process_inheritance(fork_context):
    writer = Writer()

    logger.add(writer, format="{message}", enqueue=True, catch=False)

    process = fork_context.Process(target=subworker_remove_inheritance)
    process.start()
    process.join()

    assert process.exitcode == 0

    logger.info("Main")
    logger.remove()

    assert writer.read() == "Child\nMain\n"


@pytest.mark.skipif(platform.python_implementation() == "PyPy", reason="PyPy bug #3630")
def test_remove_in_main_process_spawn(spawn_context):
    # Actually, this test may fail if sleep time in main process is too small (and no barrier used)
    # In such situation, it seems the child process has not enough time to initialize itself
    # It may fail with an "EOFError" during unpickling of the (garbage collected / closed) Queue
    writer = Writer()
    barrier = spawn_context.Barrier(2)

    logger.add(writer, format="{message}", enqueue=True, catch=False)

    process = spawn_context.Process(target=subworker_barrier, args=(logger, barrier))
    process.start()
    barrier.wait()
    logger.info("Main")
    logger.remove()
    process.join()

    assert process.exitcode == 0

    assert writer.read() == "Child\nMain\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_remove_in_main_process_fork(fork_context):
    writer = Writer()
    barrier = fork_context.Barrier(2)

    logger.add(writer, format="{message}", enqueue=True, catch=False)

    process = fork_context.Process(target=subworker_barrier, args=(logger, barrier))
    process.start()
    barrier.wait()
    logger.info("Main")
    logger.remove()
    process.join()

    assert process.exitcode == 0

    assert writer.read() == "Child\nMain\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_remove_in_main_process_inheritance(fork_context):
    writer = Writer()
    barrier = fork_context.Barrier(2)

    logger.add(writer, format="{message}", enqueue=True, catch=False)

    process = fork_context.Process(target=subworker_barrier_inheritance, args=(barrier,))
    process.start()
    barrier.wait()
    logger.info("Main")
    logger.remove()
    process.join()

    assert process.exitcode == 0

    assert writer.read() == "Child\nMain\n"


@pytest.mark.skipif(platform.python_implementation() == "PyPy", reason="PyPy bug #3630")
@pytest.mark.parametrize("loop_is_none", [True, False])
def test_await_complete_spawn(capsys, spawn_context, loop_is_none):
    async def writer(msg):
        print(msg, end="")

    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    loop = None if loop_is_none else new_loop

    logger.add(writer, format="{message}", loop=loop, enqueue=True, catch=False)

    process = spawn_context.Process(target=subworker_complete, args=(logger,))
    process.start()
    process.join()

    assert process.exitcode == 0

    async def local():
        await logger.complete()

    new_loop.run_until_complete(local())

    out, err = capsys.readouterr()
    assert out == "Child\n"
    assert err == ""


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
@pytest.mark.parametrize("loop_is_none", [True, False])
def test_await_complete_fork(capsys, loop_is_none, fork_context):
    async def writer(msg):
        print(msg, end="")

    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    loop = None if loop_is_none else new_loop

    logger.add(writer, format="{message}", loop=loop, enqueue=True, catch=False)

    process = fork_context.Process(target=subworker_complete, args=(logger,))
    process.start()
    process.join()

    assert process.exitcode == 0

    async def local():
        await logger.complete()

    new_loop.run_until_complete(local())

    out, err = capsys.readouterr()
    assert out == "Child\n"
    assert err == ""


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
@pytest.mark.parametrize("loop_is_none", [True, False])
def test_await_complete_inheritance(capsys, loop_is_none, fork_context):
    async def writer(msg):
        print(msg, end="")

    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    loop = None if loop_is_none else new_loop

    logger.add(writer, format="{message}", loop=loop, enqueue=True, catch=False)

    process = fork_context.Process(target=subworker_complete_inheritance)
    process.start()
    process.join()

    assert process.exitcode == 0

    async def local():
        await logger.complete()

    new_loop.run_until_complete(local())

    out, err = capsys.readouterr()
    assert out == "Child\n"
    assert err == ""


@pytest.mark.skipif(platform.python_implementation() == "PyPy", reason="PyPy bug #3630")
def test_not_picklable_sinks_spawn(spawn_context, tmpdir, capsys):
    filepath = tmpdir.join("test.log")
    stream = sys.stderr
    output = []

    logger.add(str(filepath), format="{message}", enqueue=True, catch=False)
    logger.add(stream, format="{message}", enqueue=True)
    logger.add(lambda m: output.append(m), format="{message}", enqueue=True)

    process = spawn_context.Process(target=subworker, args=[logger])
    process.start()
    process.join()

    assert process.exitcode == 0

    logger.info("Main")
    logger.remove()

    out, err = capsys.readouterr()

    assert filepath.read() == "Child\nMain\n"
    assert out == ""
    assert err == "Child\nMain\n"
    assert output == ["Child\n", "Main\n"]


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_not_picklable_sinks_fork(capsys, tmpdir, fork_context):
    filepath = tmpdir.join("test.log")
    stream = sys.stderr
    output = []

    logger.add(str(filepath), format="{message}", enqueue=True, catch=False)
    logger.add(stream, format="{message}", enqueue=True, catch=False)
    logger.add(lambda m: output.append(m), format="{message}", enqueue=True, catch=False)

    process = fork_context.Process(target=subworker, args=[logger])
    process.start()
    process.join()

    assert process.exitcode == 0

    logger.info("Main")
    logger.remove()

    out, err = capsys.readouterr()

    assert filepath.read() == "Child\nMain\n"
    assert out == ""
    assert err == "Child\nMain\n"
    assert output == ["Child\n", "Main\n"]


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_not_picklable_sinks_inheritance(capsys, tmpdir, fork_context):
    filepath = tmpdir.join("test.log")
    stream = sys.stderr
    output = []

    logger.add(str(filepath), format="{message}", enqueue=True, catch=False)
    logger.add(stream, format="{message}", enqueue=True, catch=False)
    logger.add(lambda m: output.append(m), format="{message}", enqueue=True, catch=False)

    process = fork_context.Process(target=subworker_inheritance)
    process.start()
    process.join()

    assert process.exitcode == 0

    logger.info("Main")
    logger.remove()

    out, err = capsys.readouterr()

    assert filepath.read() == "Child\nMain\n"
    assert out == ""
    assert err == "Child\nMain\n"
    assert output == ["Child\n", "Main\n"]


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
@pytest.mark.skipif(sys.version_info < (3, 7), reason="No 'os.register_at_fork()' function")
@pytest.mark.parametrize("enqueue", [True, False])
@pytest.mark.parametrize("deepcopied", [True, False])
def test_no_deadlock_if_internal_lock_in_use(tmpdir, enqueue, deepcopied, fork_context):
    if deepcopied:
        logger_ = copy.deepcopy(logger)
    else:
        logger_ = logger

    output = tmpdir.join("stdout.txt")
    stdout = output.open("w")

    def slow_sink(msg):
        time.sleep(0.5)
        stdout.write(msg)
        stdout.flush()

    def main():
        logger_.info("Main")

    def worker():
        logger_.info("Child")

    logger_.add(slow_sink, format="{message}", enqueue=enqueue, catch=False)

    thread = threading.Thread(target=main)
    thread.start()

    process = fork_context.Process(target=worker)
    process.start()

    thread.join()
    process.join(1)

    assert process.exitcode == 0

    logger_.remove()

    assert output.read() in ("Main\nChild\n", "Child\nMain\n")


@pytest.mark.skipif(sys.version_info < (3, 7), reason="No 'os.register_at_fork()' function")
@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
@pytest.mark.parametrize("enqueue", [True, False])
def test_no_deadlock_if_external_lock_in_use(enqueue, capsys, fork_context):
    # Can't reproduce the bug on pytest (even if stderr is not wrapped), but let it anyway
    logger.add(sys.stderr, enqueue=enqueue, catch=True, format="{message}")
    num = 100

    for i in range(num):
        logger.info("This is a message: {}", i)
        process = fork_context.Process(target=lambda: None)
        process.start()
        process.join(1)
        assert process.exitcode == 0

    logger.remove()

    out, err = capsys.readouterr()
    assert out == ""
    assert err == "".join("This is a message: %d\n" % i for i in range(num))


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
@pytest.mark.skipif(platform.python_implementation() == "PyPy", reason="PyPy is too slow")
def test_complete_from_multiple_child_processes(capsys, fork_context):
    logger.add(lambda _: None, enqueue=True, catch=False)
    num = 100

    barrier = fork_context.Barrier(num)

    def worker(barrier):
        barrier.wait()
        logger.complete()

    processes = []

    for _ in range(num):
        process = fork_context.Process(target=worker, args=(barrier,))
        process.start()
        processes.append(process)

    for process in processes:
        process.join(5)
        assert process.exitcode == 0

    out, err = capsys.readouterr()
    assert out == err == ""
