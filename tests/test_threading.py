from threading import Thread, Barrier
import itertools
from loguru import logger
import time


class NonSafeSink:
    def __init__(self):
        self.written = ""

    def write(self, message):
        self.written += message
        time.sleep(1)
        self.written += message


def test_safe_logging():
    barrier = Barrier(2)
    counter = itertools.count()

    sink = NonSafeSink()
    logger.add(sink, format="{message}", catch=False)

    def threaded():
        barrier.wait()
        logger.info("{}", next(counter))

    threads = [Thread(target=threaded) for _ in range(2)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert sink.written == "0\n0\n1\n1\n"


def test_safe_adding_while_logging(writer):
    barrier = Barrier(2)
    counter = itertools.count()

    sink_1 = NonSafeSink()
    sink_2 = NonSafeSink()
    logger.add(sink_1, format="{message}", catch=False)
    logger.add(sink_2, format="-> {message}", catch=False)

    def thread_1():
        barrier.wait()
        logger.info("{}", next(counter))

    def thread_2():
        barrier.wait()
        time.sleep(0.5)
        logger.add(writer, format="{message}", catch=False)
        logger.info("{}", next(counter))

    threads = [Thread(target=thread_1), Thread(target=thread_2)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert sink_1.written == "0\n0\n1\n1\n"
    assert sink_2.written == "-> 0\n-> 0\n-> 1\n-> 1\n"
    assert writer.read() == "1\n"


def test_safe_removing_while_logging():
    barrier = Barrier(2)
    counter = itertools.count()

    sink_1 = NonSafeSink()
    sink_2 = NonSafeSink()
    a = logger.add(sink_1, format="{message}", catch=False)
    b = logger.add(sink_2, format="-> {message}", catch=False)

    def thread_1():
        barrier.wait()
        logger.info("{}", next(counter))

    def thread_2():
        barrier.wait()
        time.sleep(0.5)
        logger.remove(b)
        logger.info("{}", next(counter))

    threads = [Thread(target=thread_1), Thread(target=thread_2)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert sink_1.written == "0\n0\n1\n1\n"
    assert sink_2.written == "-> 0\n-> 0\n"
