import asyncio
import sys
import threading
from unittest.mock import MagicMock

import pytest

from loguru import logger
from loguru._contextvars import load_contextvar_class


def test_contextualize(writer):
    logger.add(writer, format="{message} {extra[foo]} {extra[baz]}")

    with logger.contextualize(foo="bar", baz=123):
        logger.info("Contextualized")

    assert writer.read() == "Contextualized bar 123\n"


def test_contextualize_as_decorator(writer):
    logger.add(writer, format="{message} {extra[foo]} {extra[baz]}")

    @logger.contextualize(foo=123, baz="bar")
    def task():
        logger.info("Contextualized")

    task()

    assert writer.read() == "Contextualized 123 bar\n"


def test_contextualize_in_function(writer):
    logger.add(writer, format="{message} {extra}")

    def foobar():
        logger.info("Foobar!")

    with logger.contextualize(foobar="baz"):
        foobar()

    assert writer.read() == "Foobar! {'foobar': 'baz'}\n"


def test_contextualize_reset():
    contexts = []
    output = []

    def sink(message):
        contexts.append(message.record["extra"])
        output.append(str(message))

    logger.add(sink, format="{level} {message}")

    logger.info("A")

    with logger.contextualize(abc="def"):
        logger.debug("B")
        logger.warning("C")

    logger.info("D")

    assert contexts == [{}, {"abc": "def"}, {"abc": "def"}, {}]
    assert output == ["INFO A\n", "DEBUG B\n", "WARNING C\n", "INFO D\n"]


@pytest.mark.xfail(sys.version_info < (3, 5, 3), reason="ContextVar backport not supported")
def test_contextualize_async(writer):
    logger.add(writer, format="{message} {extra[i]}", catch=False)

    async def task():
        logger.info("Start")
        await asyncio.sleep(0.1)
        logger.info("End")

    async def worker(i):
        with logger.contextualize(i=i):
            await task()

    async def main():
        workers = [worker(i) for i in range(5)]
        await asyncio.gather(*workers)
        await logger.complete()

    asyncio.run(main())

    assert sorted(writer.read().splitlines()) == ["End %d" % i for i in range(5)] + [
        "Start %d" % i for i in range(5)
    ]


def test_contextualize_thread(writer):
    logger.add(writer, format="{message} {extra[i]}")

    def task():
        logger.info("Processing")

    def worker(entry_barrier, exit_barrier, i):
        with logger.contextualize(i=i):
            entry_barrier.wait()
            task()
            exit_barrier.wait()

    entry_barrier = threading.Barrier(5)
    exit_barrier = threading.Barrier(5)

    threads = [
        threading.Thread(target=worker, args=(entry_barrier, exit_barrier, i)) for i in range(5)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert sorted(writer.read().splitlines()) == ["Processing %d" % i for i in range(5)]


def test_contextualize_before_bind(writer):
    logger.add(writer, format="{message} {extra[foobar]}")

    logger_2 = logger.bind(foobar="baz")

    with logger.contextualize(foobar="baz_2"):
        logger.info("A")
        logger_2.info("B")

    logger_2.info("C")

    assert writer.read() == "A baz_2\nB baz\nC baz\n"


def test_contextualize_after_bind(writer):
    logger.add(writer, format="{message} {extra[foobar]}")

    with logger.contextualize(foobar="baz"):
        logger_2 = logger.bind(foobar="baz_2")
        logger.info("A")
        logger_2.info("B")

    logger_2.info("C")

    assert writer.read() == "A baz\nB baz_2\nC baz_2\n"


def test_contextualize_using_bound(writer):
    logger.add(writer, format="{message} {extra[foobar]}")

    logger_2 = logger.bind(foobar="baz")

    with logger_2.contextualize(foobar="baz_2"):
        logger.info("A")
        logger_2.info("B")

    logger_2.info("C")

    assert writer.read() == "A baz_2\nB baz\nC baz\n"


def test_contextualize_before_configure(writer):
    logger.add(writer, format="{message} {extra[foobar]}")

    logger.configure(extra={"foobar": "baz"})

    with logger.contextualize(foobar="baz_2"):
        logger.info("A")

    logger.info("B")

    assert writer.read() == "A baz_2\nB baz\n"


def test_contextualize_after_configure(writer):
    logger.add(writer, format="{message} {extra[foobar]}")

    with logger.contextualize(foobar="baz"):
        logger.configure(extra={"foobar": "baz_2"})
        logger.info("A")

    logger.info("B")

    assert writer.read() == "A baz\nB baz_2\n"


def test_nested_contextualize(writer):
    logger.add(writer, format="{message} {extra[foobar]}")

    with logger.contextualize(foobar="a"):
        with logger.contextualize(foobar="b"):
            logger.info("B")

        logger.info("A")

        with logger.contextualize(foobar="c"):
            logger.info("C")

    assert writer.read() == "B b\nA a\nC c\n"


def test_context_reset_despite_error(writer):
    logger.add(writer, format="{message} {extra}")

    try:
        with logger.contextualize(foobar=456):
            logger.info("Division")
            1 / 0  # noqa: B018
    except ZeroDivisionError:
        logger.info("Error")

    assert writer.read() == "Division {'foobar': 456}\nError {}\n"


# There is not CI runner available for Python 3.5.2. Consequently, we are just
# verifying third-library is properly imported to reach 100% coverage.
def test_contextvars_fallback_352(monkeypatch):
    mock_module = MagicMock()
    with monkeypatch.context() as context:
        context.setattr(sys, "version_info", (3, 5, 2))
        context.setitem(sys.modules, "contextvars", mock_module)
        assert load_contextvar_class() == mock_module.ContextVar
