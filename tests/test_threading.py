import itertools
import time
from threading import Barrier, Thread

from loguru import logger


class NonSafeSink:
    def __init__(self, sleep_time):
        self.sleep_time = sleep_time
        self.written = ""
        self.stopped = False

    def write(self, message):
        if self.stopped:
            raise RuntimeError("Can't write on stopped sink")

        length = len(message)
        self.written += message[:length]
        time.sleep(self.sleep_time)
        self.written += message[length:]

    def stop(self):
        self.stopped = True


def test_safe_logging():
    barrier = Barrier(2)
    counter = itertools.count()

    sink = NonSafeSink(1)
    logger.add(sink, format="{message}", catch=False)

    def threaded():
        barrier.wait()
        logger.info("___{}___", next(counter))

    threads = [Thread(target=threaded) for _ in range(2)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    logger.remove()

    assert sink.written in ("___0___\n___1___\n", "___1___\n___0___\n")


def test_safe_adding_while_logging(writer):
    barrier = Barrier(2)
    counter = itertools.count()

    sink_1 = NonSafeSink(1)
    sink_2 = NonSafeSink(1)
    logger.add(sink_1, format="{message}", catch=False)

    def thread_1():
        barrier.wait()
        logger.info("aaa{}bbb", next(counter))

    def thread_2():
        barrier.wait()
        time.sleep(0.5)
        logger.add(sink_2, format="{message}", catch=False)
        logger.info("ccc{}ddd", next(counter))

    threads = [Thread(target=thread_1), Thread(target=thread_2)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    logger.remove()

    assert sink_1.written == "aaa0bbb\nccc1ddd\n"
    assert sink_2.written == "ccc1ddd\n"


def test_safe_removing_while_logging(capsys):
    barrier = Barrier(2)
    counter = itertools.count()

    sink = NonSafeSink(1)
    i = logger.add(sink, format="{message}", catch=False)

    def thread_1():
        barrier.wait()
        logger.info("aaa{}bbb", next(counter))

    def thread_2():
        barrier.wait()
        time.sleep(0.5)
        logger.remove(i)
        logger.info("ccc{}ddd", next(counter))

    threads = [Thread(target=thread_1), Thread(target=thread_2)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""
    assert sink.written == "aaa0bbb\n"


def test_safe_writing_after_removing(capsys):
    barrier = Barrier(2)

    logger.add(NonSafeSink(1), format="{message}", catch=False)
    i = logger.add(NonSafeSink(1), format="{message}", catch=False)

    def write():
        barrier.wait()
        logger.info("Writing")

    def remove():
        barrier.wait()
        time.sleep(0.5)
        logger.remove(i)

    threads = [Thread(target=write), Thread(target=remove)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    logger.remove()

    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""


def test_heavily_threaded_logging(capsys):
    logger.remove()

    def function():
        i = logger.add(NonSafeSink(0.1), format="{message}", catch=False)
        logger.debug("AAA")
        logger.info("BBB")
        logger.success("CCC")
        logger.remove(i)

    threads = [Thread(target=function) for _ in range(10)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    logger.remove()

    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""
