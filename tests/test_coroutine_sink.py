import asyncio
import logging
import multiprocessing
import re
import sys
import threading

import pytest

from loguru import logger


async def async_writer(msg):
    await asyncio.sleep(0.01)
    print(msg, end="")


class AsyncWriter:
    async def __call__(self, msg):
        await asyncio.sleep(0.01)
        print(msg, end="")


def test_coroutine_function(capsys):
    async def worker():
        logger.debug("A message")
        await logger.complete()

    logger.add(async_writer, format="{message}")

    asyncio.run(worker())

    out, err = capsys.readouterr()
    assert err == ""
    assert out == "A message\n"


def test_async_callable_sink(capsys):
    async def worker():
        logger.debug("A message")
        await logger.complete()

    logger.add(AsyncWriter(), format="{message}")

    asyncio.run(worker())

    out, err = capsys.readouterr()
    assert err == ""
    assert out == "A message\n"


def test_concurrent_execution(capsys):
    async def task(i):
        logger.debug("=> {}", i)

    async def main():
        tasks = [task(i) for i in range(10)]
        await asyncio.gather(*tasks)
        await logger.complete()

    logger.add(async_writer, format="{message}")

    asyncio.run(main())

    out, err = capsys.readouterr()
    assert err == ""
    assert sorted(out.splitlines()) == sorted("=> %d" % i for i in range(10))


def test_recursive_coroutine(capsys):
    async def task(i):
        if i == 0:
            await logger.complete()
            return
        logger.info("{}!", i)
        await task(i - 1)

    logger.add(async_writer, format="{message}")

    asyncio.run(task(9))

    out, err = capsys.readouterr()
    assert err == ""
    assert sorted(out.splitlines()) == sorted("%d!" % i for i in range(1, 10))


@pytest.mark.skipif(sys.version_info < (3, 5, 3), reason="Coroutine can't access running loop")
def test_using_another_event_loop(capsys):
    async def worker():
        logger.debug("A message")
        await logger.complete()

    loop = asyncio.new_event_loop()

    logger.add(async_writer, format="{message}", loop=loop)

    loop.run_until_complete(worker())

    out, err = capsys.readouterr()
    assert err == ""
    assert out == "A message\n"


def test_run_mutiple_different_loops(capsys):
    async def worker(i):
        logger.debug("Message {}", i)
        await logger.complete()

    logger.add(async_writer, format="{message}", loop=None)

    asyncio.run(worker(1))
    asyncio.run(worker(2))

    out, err = capsys.readouterr()
    assert err == ""
    assert out == "Message 1\nMessage 2\n"


@pytest.mark.skipif(sys.version_info < (3, 5, 3), reason="Coroutine can't access running loop")
def test_run_multiple_same_loop(capsys):
    async def worker(i):
        logger.debug("Message {}", i)
        await logger.complete()

    loop = asyncio.new_event_loop()

    logger.add(async_writer, format="{message}", loop=loop)

    loop.run_until_complete(worker(1))
    loop.run_until_complete(worker(2))

    out, err = capsys.readouterr()
    assert err == ""
    assert out == "Message 1\nMessage 2\n"


def test_using_sink_without_running_loop_not_none(capsys):
    loop = asyncio.new_event_loop()

    logger.add(sys.stderr, format="=> {message}")
    logger.add(async_writer, format="{message}", loop=loop)

    logger.info("A message")

    loop.run_until_complete(logger.complete())

    out, err = capsys.readouterr()
    assert err == "=> A message\n"
    assert out == "A message\n"


def test_using_sink_without_running_loop_none(capsys):
    loop = asyncio.new_event_loop()

    logger.add(sys.stderr, format="=> {message}")
    logger.add(async_writer, format="{message}", loop=None)

    logger.info("A message")

    loop.run_until_complete(logger.complete())

    out, err = capsys.readouterr()
    assert err == "=> A message\n"
    assert out == ""


def test_global_loop_not_used(capsys):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    logger.add(sys.stderr, format="=> {message}")
    logger.add(async_writer, format="{message}", loop=None)

    logger.info("A message")

    loop.run_until_complete(logger.complete())

    out, err = capsys.readouterr()
    assert err == "=> A message\n"
    assert out == ""


@pytest.mark.skipif(sys.version_info < (3, 5, 3), reason="Coroutine can't access running loop")
def test_complete_in_another_run(capsys):
    async def worker_1():
        logger.debug("A")

    async def worker_2():
        logger.debug("B")
        await logger.complete()

    loop = asyncio.new_event_loop()

    logger.add(async_writer, format="{message}", loop=loop)

    loop.run_until_complete(worker_1())
    loop.run_until_complete(worker_2())

    out, err = capsys.readouterr()
    assert out == "A\nB\n"
    assert err == ""


def test_tasks_cancelled_on_remove(capsys):
    logger.add(async_writer, format="{message}", catch=False)

    async def foo():
        logger.info("A")
        logger.info("B")
        logger.info("C")
        logger.remove()
        await logger.complete()

    asyncio.run(foo())

    out, err = capsys.readouterr()
    assert out == err == ""


def test_remove_without_tasks(capsys):
    logger.add(async_writer, format="{message}", catch=False)
    logger.remove()

    async def foo():
        logger.info("!")
        await logger.complete()

    asyncio.run(foo())

    out, err = capsys.readouterr()
    assert out == err == ""


def test_complete_without_tasks(capsys):
    logger.add(async_writer, catch=False)

    async def worker():
        await logger.complete()

    asyncio.run(worker())

    out, err = capsys.readouterr()
    assert out == err == ""


def test_complete_stream_noop(capsys):
    logger.add(sys.stderr, format="{message}", catch=False)
    logger.info("A")

    async def worker():
        logger.info("B")
        await logger.complete()
        logger.info("C")

    asyncio.run(worker())

    logger.info("D")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == "A\nB\nC\nD\n"


def test_complete_file_noop(tmp_path):
    filepath = tmp_path / "test.log"

    logger.add(filepath, format="{message}", catch=False)
    logger.info("A")

    async def worker():
        logger.info("B")
        await logger.complete()
        logger.info("C")

    asyncio.run(worker())

    logger.info("D")

    assert filepath.read_text() == "A\nB\nC\nD\n"


def test_complete_function_noop():
    out = ""

    def write(msg):
        nonlocal out
        out += msg

    logger.add(write, format="{message}", catch=False)
    logger.info("A")

    async def worker():
        logger.info("B")
        await logger.complete()
        logger.info("C")

    asyncio.run(worker())

    logger.info("D")

    assert out == "A\nB\nC\nD\n"


def test_complete_standard_noop(capsys):
    logger.add(logging.StreamHandler(sys.stderr), format="{message}", catch=False)
    logger.info("A")

    async def worker():
        logger.info("B")
        await logger.complete()
        logger.info("C")

    asyncio.run(worker())

    logger.info("D")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == "A\nB\nC\nD\n"


def test_exception_in_coroutine_caught(capsys):
    async def sink(msg):
        raise Exception("Oh no")

    async def main():
        logger.add(sink, catch=True)
        logger.info("Hello world")
        await asyncio.sleep(0.1)
        await logger.complete()

    asyncio.run(main())

    out, err = capsys.readouterr()
    lines = err.strip().splitlines()

    assert out == ""
    assert lines[0] == "--- Logging error in Loguru Handler #0 ---"
    assert re.match(r"Record was: \{.*Hello world.*\}", lines[1])
    assert lines[-2] == "Exception: Oh no"
    assert lines[-1] == "--- End of logging error ---"


def test_exception_in_coroutine_not_caught(capsys, caplog):
    async def sink(msg):
        raise ValueError("Oh no")

    async def main():
        logger.add(sink, catch=False)
        logger.info("Hello world")
        await asyncio.sleep(0.1)
        await logger.complete()

    asyncio.run(main())

    out, err = capsys.readouterr()
    assert out == err == ""

    records = caplog.records
    assert len(records) == 1
    record = records[0]

    message = record.getMessage()
    assert "Logging error in Loguru Handler" not in message
    assert "was never retrieved" not in message

    exc_type, exc_value, _ = record.exc_info
    assert exc_type == ValueError
    assert str(exc_value) == "Oh no"


def test_exception_in_coroutine_during_complete_caught(capsys):
    async def sink(msg):
        await asyncio.sleep(0.1)
        raise Exception("Oh no")

    async def main():
        logger.add(sink, catch=True)
        logger.info("Hello world")
        await logger.complete()

    asyncio.run(main())

    out, err = capsys.readouterr()
    lines = err.strip().splitlines()

    assert out == ""
    assert lines[0] == "--- Logging error in Loguru Handler #0 ---"
    assert re.match(r"Record was: \{.*Hello world.*\}", lines[1])
    assert lines[-2] == "Exception: Oh no"
    assert lines[-1] == "--- End of logging error ---"


def test_exception_in_coroutine_during_complete_not_caught(capsys, caplog):
    async def sink(msg):
        await asyncio.sleep(0.1)
        raise ValueError("Oh no")

    async def main():
        logger.add(sink, catch=False)
        logger.info("Hello world")
        await logger.complete()

    asyncio.run(main())

    out, err = capsys.readouterr()
    assert out == err == ""

    records = caplog.records
    assert len(records) == 1
    record = records[0]

    message = record.getMessage()
    assert "Logging error in Loguru Handler" not in message
    assert "was never retrieved" not in message

    exc_type, exc_value, _ = record.exc_info
    assert exc_type == ValueError
    assert str(exc_value) == "Oh no"


@pytest.mark.skipif(sys.version_info < (3, 5, 3), reason="Coroutine can't access running loop")
def test_enqueue_coroutine_loop(capsys):
    loop = asyncio.new_event_loop()
    logger.add(async_writer, enqueue=True, loop=loop, format="{message}", catch=False)

    async def worker():
        logger.info("A")
        await logger.complete()

    loop.run_until_complete(worker())

    out, err = capsys.readouterr()
    assert out == "A\n"
    assert err == ""


def test_enqueue_coroutine_from_inside_coroutine_without_loop(capsys):
    loop = asyncio.new_event_loop()

    async def worker():
        logger.add(async_writer, enqueue=True, loop=None, format="{message}", catch=False)
        logger.info("A")
        await logger.complete()

    loop.run_until_complete(worker())

    out, err = capsys.readouterr()
    assert out == "A\n"
    assert err == ""


def test_custom_complete_function(capsys):
    awaited = False

    class Handler:
        def write(self, message):
            print(message, end="")

        async def complete(self):
            nonlocal awaited
            awaited = True

    async def worker():
        logger.info("A")
        await logger.complete()

    logger.add(Handler(), catch=False, format="{message}")

    asyncio.run(worker())

    out, err = capsys.readouterr()
    assert out == "A\n"
    assert err == ""
    assert awaited


@pytest.mark.skipif(sys.version_info < (3, 5, 3), reason="Coroutine can't access running loop")
@pytest.mark.parametrize("loop_is_none", [True, False])
def test_complete_from_another_loop(capsys, loop_is_none):
    main_loop = asyncio.new_event_loop()
    second_loop = asyncio.new_event_loop()

    loop = None if loop_is_none else main_loop
    logger.add(async_writer, loop=loop, format="{message}")

    async def worker_1():
        logger.info("A")

    async def worker_2():
        await logger.complete()

    main_loop.run_until_complete(worker_1())
    second_loop.run_until_complete(worker_2())

    out, err = capsys.readouterr()
    assert out == err == ""

    main_loop.run_until_complete(worker_2())

    out, err = capsys.readouterr()
    assert out == "A\n"
    assert err == ""


def test_complete_from_multiple_threads_loop_is_none(capsys):
    async def worker(i):
        for _ in range(100):
            await asyncio.sleep(0)
            logger.info("{:03}", i)
        await logger.complete()

    async def sink(msg):
        print(msg, end="")

    def worker_(i):
        asyncio.run(worker(i))

    logger.add(sink, catch=False, format="{message}")

    threads = [threading.Thread(target=worker_, args=(i,)) for i in range(10)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    out, err = capsys.readouterr()
    assert sorted(out.splitlines()) == ["{:03}".format(i) for i in range(10) for _ in range(100)]
    assert err == ""


def test_complete_from_multiple_threads_loop_is_not_none(capsys):
    async def worker(i):
        for _ in range(100):
            await asyncio.sleep(0)
            logger.info("{:03}", i)
        await logger.complete()

    async def sink(msg):
        print(msg, end="")

    def worker_(i):
        asyncio.run(worker(i))

    loop = asyncio.new_event_loop()
    logger.add(sink, catch=False, format="{message}", loop=loop)

    threads = [threading.Thread(target=worker_, args=(i,)) for i in range(10)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    async def complete():
        await logger.complete()

    loop.run_until_complete(complete())

    out, err = capsys.readouterr()
    assert sorted(out.splitlines()) == ["{:03}".format(i) for i in range(10) for _ in range(100)]
    assert err == ""


def test_complete_and_sink_write_concurrency():
    count = 1000
    n = 0

    async def sink(message):
        nonlocal n
        n += 1

    async def some_task():
        for _ in range(count):
            logger.info("Message")
            await asyncio.sleep(0)

    async def another_task():
        for _ in range(count):
            await logger.complete()
            await asyncio.sleep(0)

    async def main():
        logger.remove()
        logger.add(sink, catch=False)

        await asyncio.gather(some_task(), another_task())

    asyncio.run(main())

    assert n == count


def test_complete_and_contextualize_concurrency():
    called = False

    async def main():
        logging_event = asyncio.Event()
        contextualize_event = asyncio.Event()

        async def sink(message):
            nonlocal called
            logging_event.set()
            await contextualize_event.wait()
            called = True

        async def logging_task():
            logger.info("Message")
            await logger.complete()

        async def contextualize_task():
            with logger.contextualize():
                contextualize_event.set()
                await logging_event.wait()

        logger.remove()
        logger.add(sink, catch=False)

        await asyncio.gather(logging_task(), contextualize_task())

    asyncio.run(main())

    assert called


async def async_subworker(logger_):
    logger_.info("Child")
    await logger_.complete()


async def async_mainworker(logger_):
    logger_.info("Main")
    await logger_.complete()


def subworker(logger_):
    loop = asyncio.new_event_loop()
    loop.run_until_complete(async_subworker(logger_))


class Writer:
    def __init__(self):
        self.output = ""

    async def write(self, message):
        self.output += message


def test_complete_with_sub_processes(capsys):
    spawn_context = multiprocessing.get_context("spawn")

    loop = asyncio.new_event_loop()
    writer = Writer()
    logger.add(writer.write, context=spawn_context, format="{message}", enqueue=True, loop=loop)

    process = spawn_context.Process(target=subworker, args=[logger])
    process.start()
    process.join()

    async def complete():
        await logger.complete()

    loop.run_until_complete(complete())

    out, err = capsys.readouterr()
    assert out == err == ""
    assert writer.output == "Child\n"


@pytest.mark.skipif(sys.version_info < (3, 5, 3), reason="Coroutine can't access running loop")
def test_invalid_coroutine_sink_if_no_loop_with_enqueue():
    with pytest.raises(ValueError):
        logger.add(async_writer, enqueue=True, loop=None)
