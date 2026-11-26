import itertools
from threading import Barrier, Event, Lock, Thread

import pytest

import loguru
from loguru import logger

TIMEOUT = 5


class ObservedLock:
    """Handler lock which records when a thread has to wait for it."""

    def __init__(self):
        self._lock = Lock()
        self.contended = Event()

    def __enter__(self):
        if not self._lock.acquire(blocking=False):
            self.contended.set()
            self._lock.acquire()

    def __exit__(self, *args):
        self._lock.release()


@pytest.fixture
def handler_locks(monkeypatch):
    locks = []

    def create_handler_lock():
        lock = ObservedLock()
        locks.append(lock)
        return lock

    monkeypatch.setattr(loguru._handler, "create_handler_lock", create_handler_lock)
    return locks


class NonSafeSink:
    def __init__(self, paused=False):
        self.written = ""
        self.stopped = False
        self.writing = Event()
        self.stopping = Event()
        self.resume = Event()
        if not paused:
            self.resume.set()

    def write(self, message):
        if self.stopped:
            raise RuntimeError("Can't write on stopped sink")

        length = len(message) // 2
        self.written += message[:length]
        self.writing.set()
        self.resume.wait()
        self.written += message[length:]

    def stop(self):
        self.stopping.set()
        self.resume.wait()
        self.stopped = True


def test_safe_logging(handler_locks):
    barrier = Barrier(2)
    counter = itertools.count()

    sink = NonSafeSink(paused=True)
    logger.add(sink, format="{message}", catch=False)
    (lock,) = handler_locks

    def threaded():
        barrier.wait()
        logger.info("___{}___", next(counter))

    threads = [Thread(target=threaded) for _ in range(2)]

    for thread in threads:
        thread.start()

    sink.writing.wait()
    blocked = lock.contended.wait(TIMEOUT)
    sink.resume.set()

    for thread in threads:
        thread.join()

    logger.remove()

    assert blocked
    assert sink.written in ("___0___\n___1___\n", "___1___\n___0___\n")


def test_safe_adding_while_logging(handler_locks):
    barrier = Barrier(2)
    counter = itertools.count()

    sink_1 = NonSafeSink(paused=True)
    sink_2 = NonSafeSink()
    logger.add(sink_1, format="{message}", catch=False)
    (lock_1,) = handler_locks

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

    blocked = lock_1.contended.wait(TIMEOUT)
    sink_1.resume.set()

    for thread in threads:
        thread.join()

    logger.remove()

    assert blocked
    assert sink_1.written == "aaa0bbb\nccc1ddd\n"
    assert sink_2.written == "ccc1ddd\n"


def test_safe_removing_while_logging(capsys, handler_locks):
    barrier = Barrier(2)
    counter = itertools.count()

    sink = NonSafeSink(paused=True)
    i = logger.add(sink, format="{message}", catch=False)
    (lock,) = handler_locks

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

    blocked = lock.contended.wait(TIMEOUT)
    sink.resume.set()

    for thread in threads:
        thread.join()

    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""
    assert blocked
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


def test_safe_slow_removing_all_while_logging(capsys, handler_locks):
    barrier = Barrier(2)

    sink_1 = NonSafeSink(paused=True)
    sink_2 = NonSafeSink(paused=True)

    for sink in [sink_1, sink_2, *(NonSafeSink() for _ in range(8))]:
        logger.add(sink, format="{message}", catch=False)

    def thread_1():
        barrier.wait()
        logger.remove()

    def thread_2():
        barrier.wait()
        sink_1.stopping.wait()
        logger.info("Some message")

    threads = [Thread(target=thread_1), Thread(target=thread_2)]

    for thread in threads:
        thread.start()

    # The first handler is already removed, the message is being written to the second one.
    writing = sink_2.writing.wait(TIMEOUT)
    sink_1.resume.set()

    # The second handler is removed before the message has been fully emitted.
    blocked = handler_locks[1].contended.wait(TIMEOUT)
    sink_2.resume.set()

    for thread in threads:
        thread.join()

    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""
    assert writing
    assert blocked


def test_safe_writing_after_removing(capsys):
    barrier = Barrier(2)

    sink_1 = NonSafeSink(paused=True)
    sink_2 = NonSafeSink()
    logger.add(sink_1, format="{message}", catch=False)
    i = logger.add(sink_2, format="{message}", catch=False)

    def write():
        barrier.wait()
        logger.info("Writing")

    def remove():
        barrier.wait()
        sink_1.writing.wait()
        logger.remove(i)
        sink_1.resume.set()

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
        i = logger.add(NonSafeSink(), format="{message}", catch=False)
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
