import itertools
import time
from threading import Barrier, Event, Thread

from loguru import logger


class NonSafeSink:
    def __init__(self, sleep_time, stop_time=0, stopping=None):
        self.sleep_time = sleep_time
        self.stop_time = stop_time
        self.written = ""
        self.stopped = False
        # Set once the sink is midway through an operation, so that another thread can
        # act while it is still in progress without relying on timing. The "stopping"
        # event can be shared between sinks to wait for the first one of a group.
        self.writing = Event()
        self.stopping = Event() if stopping is None else stopping

    def write(self, message):
        if self.stopped:
            raise RuntimeError("Can't write on stopped sink")

        length = len(message)
        self.written += message[:length]
        self.writing.set()
        time.sleep(self.sleep_time)
        self.written += message[length:]

    def stop(self):
        self.stopping.set()
        time.sleep(self.stop_time)
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
        sink_1.writing.wait()
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
        sink.writing.wait()
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


def test_safe_removing_all_while_logging(capsys):
    barrier = Barrier(2)

    for _ in range(1000):
        logger.add(lambda _: None, format="{message}", catch=False)

    def thread_1():
        barrier.wait()
        logger.remove()

    def thread_2():
        barrier.wait()
        for _ in range(100):
            logger.info("Some message")

    threads = [Thread(target=thread_1), Thread(target=thread_2)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""


def test_safe_slow_removing_all_while_logging(capsys):
    barrier = Barrier(2)

    stopping = Event()

    for _ in range(10):
        sink = NonSafeSink(0.1, 0.1, stopping=stopping)
        logger.add(sink, format="{message}", catch=False)

    def thread_1():
        barrier.wait()
        logger.remove()

    def thread_2():
        barrier.wait()
        stopping.wait()
        logger.info("Some message")

    threads = [Thread(target=thread_1), Thread(target=thread_2)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""


def test_safe_writing_after_removing(capsys):
    barrier = Barrier(2)

    sink_1 = NonSafeSink(1)
    logger.add(sink_1, format="{message}", catch=False)
    i = logger.add(NonSafeSink(1), format="{message}", catch=False)

    def write():
        barrier.wait()
        logger.info("Writing")

    def remove():
        barrier.wait()
        sink_1.writing.wait()
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
