import copy
import multiprocessing
import os
import platform
import sys
import threading
import time

import pytest

from loguru import logger

from .conftest import new_event_loop_context


@pytest.fixture
def fork_context():
    return multiprocessing.get_context("fork")


@pytest.fixture
def spawn_context():
    return multiprocessing.get_context("spawn")


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
    logger_.complete()


def subworker_remove_inheritance():
    logger.info("Child")
    logger.remove()
    logger.info("Nope")
    logger.complete()


def subworker_remove_no_logging(logger_):
    logger_.remove()
    logger_.info("Nope")
    logger_.complete()


def subworker_remove_no_logging_inheritance():
    logger.remove()
    logger.info("Nope")
    logger.complete()


def subworker_complete_no_logging(logger_):
    logger_.complete()


def subworker_complete_no_logging_inheritance():
    logger.complete()


def subworker_complete(logger_):
    async def work():
        logger_.info("Child")
        await logger_.complete()

    with new_event_loop_context() as loop:
        loop.run_until_complete(work())


def subworker_complete_inheritance():
    async def work():
        logger.info("Child")
        await logger.complete()

    with new_event_loop_context() as loop:
        loop.run_until_complete(work())


def subworker_barrier(logger_, barrier_1, barrier_2):
    logger_.info("Child")
    logger_.complete()
    barrier_1.wait()
    barrier_2.wait()
    logger_.info("Nope")
    logger_.complete()


def subworker_barrier_inheritance(barrier_1, barrier_2):
    logger.info("Child")
    logger.complete()
    barrier_1.wait()
    barrier_2.wait()
    logger.info("Nope")
    logger.complete()


class Writer:
    def __init__(self):
        self._output = ""

    def write(self, message):
        self._output += message

    def read(self):
        return self._output


def test_apply_spawn(spawn_context):
    writer = Writer()

    logger.add(writer, context=spawn_context, format="{message}", enqueue=True, catch=False)

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

    logger.add(writer, context=fork_context, format="{message}", enqueue=True, catch=False)

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

    logger.add(writer, context=fork_context, format="{message}", enqueue=True, catch=False)

    with fork_context.Pool(1) as pool:
        for i in range(3):
            pool.apply(do_something, (i,))
        pool.close()
        pool.join()

    logger.info("Done!")
    logger.remove()

    assert writer.read() == "#0\n#1\n#2\nDone!\n"


def test_apply_async_spawn(spawn_context):
    writer = Writer()

    logger.add(writer, context=spawn_context, format="{message}", enqueue=True, catch=False)

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

    logger.add(writer, context=fork_context, format="{message}", enqueue=True, catch=False)

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

    logger.add(writer, context=fork_context, format="{message}", enqueue=True, catch=False)

    with fork_context.Pool(1) as pool:
        for i in range(3):
            result = pool.apply_async(do_something, (i,))
            result.get()
        pool.close()
        pool.join()

    logger.info("Done!")
    logger.remove()

    assert writer.read() == "#0\n#1\n#2\nDone!\n"


def test_process_spawn(spawn_context):
    writer = Writer()

    logger.add(writer, context=spawn_context, format="{message}", enqueue=True, catch=False)

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

    logger.add(writer, context=fork_context, format="{message}", enqueue=True, catch=False)

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

    logger.add(writer, context=fork_context, format="{message}", enqueue=True, catch=False)

    process = fork_context.Process(target=subworker_inheritance)
    process.start()
    process.join()

    assert process.exitcode == 0

    logger.info("Main")
    logger.remove()

    assert writer.read() == "Child\nMain\n"


def test_remove_in_child_process_spawn(spawn_context):
    writer = Writer()

    logger.add(writer, context=spawn_context, format="{message}", enqueue=True, catch=False)

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

    logger.add(writer, context=fork_context, format="{message}", enqueue=True, catch=False)

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

    logger.add(writer, context=fork_context, format="{message}", enqueue=True, catch=False)

    process = fork_context.Process(target=subworker_remove_inheritance)
    process.start()
    process.join()

    assert process.exitcode == 0

    logger.info("Main")
    logger.remove()

    assert writer.read() == "Child\nMain\n"


def test_remove_in_main_process_spawn(spawn_context):
    # Actually, this test may fail if sleep time in main process is too small (and no barrier used)
    # In such situation, it seems the child process has not enough time to initialize itself
    # It may fail with an "EOFError" during unpickling of the (garbage collected / closed) Queue
    writer = Writer()
    init_barrier = spawn_context.Barrier(2)
    remove_barrier = spawn_context.Barrier(2)

    logger.add(writer, context=spawn_context, format="{message}", enqueue=True, catch=False)

    process = spawn_context.Process(
        target=subworker_barrier, args=(logger, init_barrier, remove_barrier)
    )
    process.start()
    init_barrier.wait()

    logger.info("Main")
    logger.remove()
    remove_barrier.wait()
    process.join()

    assert process.exitcode == 0

    assert writer.read() == "Child\nMain\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_remove_in_main_process_fork(fork_context):
    writer = Writer()
    init_barrier = fork_context.Barrier(2)
    remove_barrier = fork_context.Barrier(2)

    logger.add(writer, context=fork_context, format="{message}", enqueue=True, catch=False)

    process = fork_context.Process(
        target=subworker_barrier, args=(logger, init_barrier, remove_barrier)
    )
    process.start()
    init_barrier.wait()
    logger.info("Main")
    logger.remove()
    remove_barrier.wait()
    process.join()

    assert process.exitcode == 0

    assert writer.read() == "Child\nMain\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_remove_in_main_process_inheritance(fork_context):
    writer = Writer()
    init_barrier = fork_context.Barrier(2)
    remove_barrier = fork_context.Barrier(2)

    logger.add(writer, context=fork_context, format="{message}", enqueue=True, catch=False)

    process = fork_context.Process(
        target=subworker_barrier_inheritance,
        args=(init_barrier, remove_barrier),
    )
    process.start()
    init_barrier.wait()
    logger.info("Main")
    logger.remove()
    remove_barrier.wait()
    process.join()

    assert process.exitcode == 0

    assert writer.read() == "Child\nMain\n"


def test_remove_in_child_without_logging_spawn(spawn_context):
    writer = Writer()

    logger.add(writer, context=spawn_context, format="{message}", enqueue=True, catch=False)

    process = spawn_context.Process(target=subworker_remove_no_logging, args=(logger,))
    process.start()
    process.join()

    assert process.exitcode == 0

    logger.info("Main")
    logger.remove()

    assert writer.read() == "Main\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_remove_in_child_without_logging_fork(fork_context):
    writer = Writer()

    logger.add(writer, context=fork_context, format="{message}", enqueue=True, catch=False)

    process = fork_context.Process(target=subworker_remove_no_logging, args=(logger,))
    process.start()
    process.join()

    assert process.exitcode == 0

    logger.info("Main")
    logger.remove()

    assert writer.read() == "Main\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_remove_in_child_without_logging_inheritance(fork_context):
    writer = Writer()

    logger.add(writer, context=fork_context, format="{message}", enqueue=True, catch=False)

    process = fork_context.Process(target=subworker_remove_no_logging_inheritance)
    process.start()
    process.join()

    assert process.exitcode == 0

    logger.info("Main")
    logger.remove()

    assert writer.read() == "Main\n"


def test_complete_in_child_without_logging_spawn(spawn_context):
    writer = Writer()

    logger.add(writer, context=spawn_context, format="{message}", enqueue=True, catch=False)

    process = spawn_context.Process(target=subworker_complete_no_logging, args=(logger,))
    process.start()
    process.join()

    assert process.exitcode == 0

    logger.info("Main")
    logger.complete()

    assert writer.read() == "Main\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_complete_in_child_without_logging_fork(fork_context):
    writer = Writer()

    logger.add(writer, context=fork_context, format="{message}", enqueue=True, catch=False)

    process = fork_context.Process(target=subworker_complete_no_logging, args=(logger,))
    process.start()
    process.join()

    assert process.exitcode == 0

    logger.info("Main")
    logger.complete()

    assert writer.read() == "Main\n"


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_complete_in_child_without_logging_inheritance(fork_context):
    writer = Writer()

    logger.add(writer, context=fork_context, format="{message}", enqueue=True, catch=False)

    process = fork_context.Process(target=subworker_complete_no_logging_inheritance)
    process.start()
    process.join()

    assert process.exitcode == 0

    logger.info("Main")
    logger.complete()

    assert writer.read() == "Main\n"


def test_await_complete_spawn(capsys, spawn_context):
    async def writer(msg):
        print(msg, end="")

    with new_event_loop_context() as loop:
        logger.add(
            writer, context=spawn_context, format="{message}", loop=loop, enqueue=True, catch=False
        )

        process = spawn_context.Process(target=subworker_complete, args=(logger,))
        process.start()
        process.join()

        assert process.exitcode == 0

        async def local():
            await logger.complete()

        loop.run_until_complete(local())

    out, err = capsys.readouterr()
    assert out == "Child\n"
    assert err == ""


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_await_complete_fork(capsys, fork_context):
    async def writer(msg):
        print(msg, end="")

    with new_event_loop_context() as loop:
        logger.add(
            writer, context=fork_context, format="{message}", loop=loop, enqueue=True, catch=False
        )

        process = fork_context.Process(target=subworker_complete, args=(logger,))
        process.start()
        process.join()

        assert process.exitcode == 0

        async def local():
            await logger.complete()

        loop.run_until_complete(local())

    out, err = capsys.readouterr()
    assert out == "Child\n"
    assert err == ""


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_await_complete_inheritance(capsys, fork_context):
    async def writer(msg):
        print(msg, end="")

    with new_event_loop_context() as loop:
        logger.add(
            writer, context=fork_context, format="{message}", loop=loop, enqueue=True, catch=False
        )

        process = fork_context.Process(target=subworker_complete_inheritance)
        process.start()
        process.join()

        assert process.exitcode == 0

        async def local():
            await logger.complete()

        loop.run_until_complete(local())

    out, err = capsys.readouterr()
    assert out == "Child\n"
    assert err == ""


def test_not_picklable_sinks_spawn(spawn_context, tmp_path, capsys):
    filepath = tmp_path / "test.log"
    stream = sys.stderr
    output = []

    logger.add(filepath, context=spawn_context, format="{message}", enqueue=True, catch=False)
    logger.add(stream, context=spawn_context, format="{message}", enqueue=True)
    logger.add(lambda m: output.append(m), context=spawn_context, format="{message}", enqueue=True)

    process = spawn_context.Process(target=subworker, args=[logger])
    process.start()
    process.join()

    assert process.exitcode == 0

    logger.info("Main")
    logger.remove()

    out, err = capsys.readouterr()

    assert filepath.read_text() == "Child\nMain\n"
    assert out == ""
    assert err == "Child\nMain\n"
    assert output == ["Child\n", "Main\n"]


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_not_picklable_sinks_fork(capsys, tmp_path, fork_context):
    filepath = tmp_path / "test.log"
    stream = sys.stderr
    output = []

    logger.add(filepath, context=fork_context, format="{message}", enqueue=True, catch=False)
    logger.add(stream, context=fork_context, format="{message}", enqueue=True, catch=False)
    logger.add(
        lambda m: output.append(m),
        context=fork_context,
        format="{message}",
        enqueue=True,
        catch=False,
    )

    process = fork_context.Process(target=subworker, args=[logger])
    process.start()
    process.join()

    assert process.exitcode == 0

    logger.info("Main")
    logger.remove()

    out, err = capsys.readouterr()

    assert filepath.read_text() == "Child\nMain\n"
    assert out == ""
    assert err == "Child\nMain\n"
    assert output == ["Child\n", "Main\n"]


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_not_picklable_sinks_inheritance(capsys, tmp_path, fork_context):
    filepath = tmp_path / "test.log"
    stream = sys.stderr
    output = []

    logger.add(filepath, context=fork_context, format="{message}", enqueue=True, catch=False)
    logger.add(stream, context=fork_context, format="{message}", enqueue=True, catch=False)
    logger.add(
        lambda m: output.append(m),
        context=fork_context,
        format="{message}",
        enqueue=True,
        catch=False,
    )

    process = fork_context.Process(target=subworker_inheritance)
    process.start()
    process.join()

    assert process.exitcode == 0

    logger.info("Main")
    logger.remove()

    out, err = capsys.readouterr()

    assert filepath.read_text() == "Child\nMain\n"
    assert out == ""
    assert err == "Child\nMain\n"
    assert output == ["Child\n", "Main\n"]


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
@pytest.mark.skipif(sys.version_info < (3, 7), reason="No 'os.register_at_fork()' function")
@pytest.mark.parametrize("enqueue", [True, False])
@pytest.mark.parametrize("deepcopied", [True, False])
def test_no_deadlock_if_internal_lock_in_use(tmp_path, enqueue, deepcopied, fork_context):
    if deepcopied:
        logger_ = copy.deepcopy(logger)
    else:
        logger_ = logger

    output = tmp_path / "stdout.txt"

    with output.open("w") as stdout:

        def slow_sink(msg):
            time.sleep(0.5)
            stdout.write(msg)
            stdout.flush()

        def main():
            logger_.info("Main")

        def worker():
            logger_.info("Child")

        logger_.add(
            slow_sink, context=fork_context, format="{message}", enqueue=enqueue, catch=False
        )

        thread = threading.Thread(target=main)
        thread.start()

        process = fork_context.Process(target=worker)
        process.start()

        thread.join()
        process.join(2)

        assert process.exitcode == 0

        logger_.remove()

    assert output.read_text() in ("Main\nChild\n", "Child\nMain\n")


@pytest.mark.skipif(sys.version_info < (3, 7), reason="No 'os.register_at_fork()' function")
@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
@pytest.mark.parametrize("enqueue", [True, False])
def test_no_deadlock_if_external_lock_in_use(enqueue, capsys, fork_context):
    # Can't reproduce the bug on pytest (even if stderr is not wrapped), but let it anyway
    logger.add(sys.stderr, context=fork_context, enqueue=enqueue, catch=True, format="{message}")
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
def test_concurrent_logging_from_multiple_children(capsys, fork_context):
    writer = Writer()
    num = 10
    log_count = 100
    sentence = "This is some message from a child process."

    barrier = fork_context.Barrier(num)

    def sink(message):
        for character in message:
            writer.write(character)

    def worker():
        barrier.wait()
        for _ in range(log_count):
            logger.info(sentence)

    logger.add(sink, context=fork_context, format="{message}", enqueue=True, catch=False)

    processes = []

    for _ in range(num):
        process = fork_context.Process(target=worker)
        process.start()
        processes.append(process)

    for process in processes:
        process.join(5)
        assert process.exitcode == 0

    logger.complete()

    assert writer.read() == (sentence + "\n") * num * log_count

    out, err = capsys.readouterr()
    assert out == err == ""


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_remove_from_main_while_child_is_processing(fork_context):
    barrier = fork_context.Barrier(2)

    count = 10000

    def worker():
        for _ in range(count):
            logger.info(".")
        barrier.wait()

    logger.add(lambda m: None, enqueue=True, context=fork_context, catch=False, format="{message}")

    process = fork_context.Process(target=worker)
    process.start()

    barrier.wait()
    logger.remove()

    process.join(1)
    assert process.exitcode == 0


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_remove_from_main_while_pipe_is_full(fork_context):
    barrier = fork_context.Barrier(2)

    def worker():
        for _ in range(10):
            logger.info("." * 100000)
        barrier.wait()

    logger.add(lambda m: None, enqueue=True, context=fork_context, catch=False, format="{message}")

    process = fork_context.Process(target=worker)
    process.start()

    barrier.wait()
    logger.remove()

    process.join(1)
    assert process.exitcode == 0


@pytest.mark.parametrize("init", [True, False])
@pytest.mark.parametrize("complete", [True, False])
@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_remove_from_main_while_children_processing_big_messages(fork_context, init, complete):
    barrier1 = fork_context.Barrier(31)
    barrier2 = fork_context.Barrier(31)

    def worker():
        barrier1.wait()
        for i in range(50):
            logger.bind(data="." * 100000).info(i)
        barrier2.wait()
        for i in range(50):
            logger.bind(data="." * 100000).info(i)
        if complete:
            logger.complete()

    logger.add(
        lambda _: None,
        enqueue=True,
        format="{message}",
        context=fork_context,
        catch=False,
    )

    if init:
        logger.info("Init")

    processes = []

    for _ in range(30):
        process = fork_context.Process(target=worker)
        process.start()
        processes.append(process)

    barrier1.wait()
    barrier2.wait()
    logger.remove()

    for process in processes:
        process.join(5)
        assert process.exitcode == 0


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
@pytest.mark.skipif(sys.version_info < (3, 7), reason="No 'os.register_at_fork()' function")
def test_log_and_complete_concurrently_initialize_queue_thread(fork_context, writer):
    def worker(i):
        barrier = threading.Barrier(2)

        def log():
            barrier.wait()
            logger.info(i)

        def complete():
            barrier.wait()
            logger.complete()

        thread_1 = threading.Thread(target=log)
        thread_2 = threading.Thread(target=complete)

        thread_1.start()
        thread_2.start()

        thread_1.join()
        thread_2.join()

    logger.add(
        writer,
        enqueue=True,
        format="{message}",
        context=fork_context,
        catch=False,
    )

    logger.info("Init")
    logger.complete()

    for i in range(100):
        process = fork_context.Process(target=worker, args=(i,))
        process.start()
        process.join(1)
        assert process.exitcode == 0

    logger.complete()

    assert writer.read() == "Init\n" + "".join("%d\n" % i for i in range(100))


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
@pytest.mark.skipif(sys.version_info < (3, 7), reason="No 'os.register_at_fork()' function")
def test_concurrent_remove_and_complete(capsys, fork_context):
    barrier = fork_context.Barrier(2)
    event = fork_context.Event()
    num = 100

    handler_ids = []

    for _ in range(num):
        handler_id = logger.add(lambda _: None, enqueue=True, context=fork_context, catch=False)
        handler_ids.append(handler_id)
        logger.info("Message")

    def worker():
        barrier.wait()
        while not event.is_set():
            logger.complete()

    process = fork_context.Process(target=worker)
    process.start()

    barrier.wait()

    for handler_id in handler_ids:
        logger.remove(handler_id)

    event.set()

    process.join(1)
    assert process.exitcode == 0

    out, err = capsys.readouterr()
    assert out == err == ""


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
@pytest.mark.skipif(sys.version_info < (3, 7), reason="No 'os.register_at_fork()' function")
def test_creating_machinery_locks_and_concurrent_forking(capsys, fork_context):
    running = True

    def worker_thread():
        while running:
            i = logger.add(lambda _: None, enqueue=True, context=fork_context, catch=False)
            logger.remove(i)

    def worker_process():
        logger.info("Message")
        logger.complete()

    thread = threading.Thread(target=worker_thread)
    thread.start()

    for _ in range(100):
        process = fork_context.Process(target=worker_process)
        process.start()
        process.join(1)
        assert process.exitcode == 0

    running = False
    thread.join()

    out, err = capsys.readouterr()
    assert out == err == ""


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
@pytest.mark.skipif(platform.python_implementation() == "PyPy", reason="PyPy is too slow")
def test_complete_from_multiple_child_processes(capsys, fork_context):
    logger.add(lambda _: None, context=fork_context, enqueue=True, catch=False)
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
    assert out == err == ""


@pytest.mark.skipif(os.name == "nt", reason="Windows does not support forking")
def test_child_ends_without_explicit_complete_call_fork(fork_context):
    writer = Writer()

    logger.add(writer, context=fork_context, format="{message}", enqueue=True, catch=False)

    process = fork_context.Process(target=subworker, args=(logger,))
    process.start()
    process.join(5)
    assert process.exitcode == 0

    logger.info("Main")
    logger.remove()

    assert writer.read() == "Child\nMain\n"


def test_child_ends_without_explicit_complete_call_spawn(spawn_context):
    writer = Writer()

    logger.add(writer, context=spawn_context, format="{message}", enqueue=True, catch=False)

    process = spawn_context.Process(target=subworker, args=(logger,))
    process.start()
    process.join(5)
    assert process.exitcode == 0

    logger.info("Main")
    logger.remove()

    assert writer.read() == "Child\nMain\n"
