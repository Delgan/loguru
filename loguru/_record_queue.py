import collections
import multiprocessing
from multiprocessing.util import Finalize
from threading import Condition, Thread

from ._locks_machinery import create_queue_lock


class RecordQueue:
    """A multiprocessing-safe queue in charge of transferring records between processes.

    The design is very closely coupled to the intended usage by the Handler class.

    This class is not fully thread-safe. Concurrent calls likely need to be protected by a Lock.
    """

    def __init__(self, multiprocessing_context, error_interceptor, handler_id):
        self._error_interceptor = error_interceptor
        self._handler_id = handler_id
        self._buffer = None
        self._multiprocessing_context = multiprocessing_context

        if self._multiprocessing_context is None:
            self._lock = multiprocessing.Lock()
            self._receiver, self._sender = multiprocessing.Pipe(duplex=False)
            self._is_closed = multiprocessing.Event()
        else:
            self._lock = self._multiprocessing_context.Lock()
            self._receiver, self._sender = self._multiprocessing_context.Pipe(duplex=False)
            self._is_closed = self._multiprocessing_context.Event()

        self._broker_thread = None
        self._condition_lock = create_queue_lock()
        self._condition = None

        self._finalize = None

        self._sentinel_stop = object()
        self._sentinel_close = object()

    def put(self, item):
        """Put a logging record in the queue and return immediately."""
        # Each process needs its own thread. However, when a child process is started, the inherited
        # thread will appear nullified ("spawn" method) or stopped ("fork" method). In such case,
        # that means that we are in a new process, and that we must therefore start a new thread.
        # To reduce repetition, this initialization strategy also applies to the owner process (the
        # thread, initially "None", is only created at the time of the first "put()" call).
        # Note that we don't need to acquire a Lock here as concurrent calls are already protected
        # by a Lock in the Handler. The Condition only serves to wake up the broker thread.
        if not self._broker_thread or not self._broker_thread.is_alive():
            # Items copied during fork must be discarded.
            self._buffer = collections.deque()

            # Must be re-created in each forked process because the number of waiters is copied.
            self._condition = Condition(self._condition_lock)

            # We must ensure the process is not abruptly terminated while the broker thread has
            # acquired the Lock. Otherwise, others processes might be blocked forever. We can't
            # expect all users to call "logger.complete()" before terminating the process, so we
            # use the undocumented "Finalize" class which allows a function to be called when the
            # process is about to terminate. This is required because "atexit.register()" is not
            # working in child processes started by "fork" method (this was fixed in latest versions
            # of CPython, though, see https://github.com/python/cpython/issues/83856).
            self._finalize = Finalize(self, self.stop, exitpriority=0)

            self._broker_thread = Thread(
                target=self._threaded_broker,
                daemon=True,
                name="loguru-broker-%d" % self._handler_id,
            )
            self._broker_thread.start()

        with self._condition:
            self._buffer.append(item)
            self._condition.notify()

    def get(self):
        """Get the next pending item from the queue (block until one is available if necessary)."""
        # The Handler calls this method from a single thread and from a single process, therefore
        # no Lock is necessary (contrary to the "put()" method which is called from multiple
        # processes).
        return self._receiver.recv()

    def put_final(self, item):
        """Put one last item in the queue and disable it for further use.

        Once the item has been processed, subsequent elements possibly added by other processes
        will be ignored. This means once the item is read from the queue, it is guaranteed that
        no other item will ever be read from it.

        This method is intended to be called exactly once to prepare termination of reader thread.
        """
        # The Handler lock protects this method call, therefore the two elements will be added
        # atomically (they are guaranteed to appear consecutively in the queue).
        self.put(self._sentinel_close)
        self.put(item)

    def stop(self):
        """Stop processing queued items and wait for the internal thread to finish.

        This method is expected to be called before closing the queue, to ensure all items have
        been processed.
        """
        if not self._broker_thread or not self._broker_thread.is_alive():
            return
        self.put(self._sentinel_stop)
        self._broker_thread.join()

    def close(self):
        """Close the queue definitively and release its internal resources.

        This method must not be called if the queue is still in use by any process. In particular,
        the queue must first be stopped and neither "put()" nor "get()" must be called afterwards or
        concurrently.

        This method should be called exactly once, generally after a call to "put_final()".
        """
        self._buffer.clear()
        self._receiver.close()
        self._sender.close()

    def is_closed(self):
        """Check whether the queue has been closed (possibly by another process).

        This avoids queuing items that will never be processed.
        """
        return self._is_closed.is_set()

    def _threaded_broker(self):
        is_final = False

        while True:
            with self._condition:
                if not self._buffer:
                    self._condition.wait()
                record = self._buffer.popleft()

            if record is self._sentinel_close:
                is_final = True
                continue

            if record is self._sentinel_stop:
                break

            try:
                with self._lock:
                    if self._is_closed.is_set():
                        continue
                    # It's crucial to toggle the "is_closed" flag and send the final record
                    # atomically (under the same lock acquisition). Other processes must not be able
                    # to send records after the one that is expected to be last.
                    self._sender.send(record)
                    if is_final:
                        self._is_closed.set()
            except Exception:
                record = record.record if hasattr(record, "record") else record
                self._error_interceptor.print(record)

    def __getstate__(self):
        state = self.__dict__.copy()
        state["_buffer"] = None
        state["_broker_thread"] = None
        state["_condition_lock"] = None
        state["_condition"] = None
        state["_finalize"] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._condition_lock = create_queue_lock()
        self._waiter_lock = create_queue_lock()  # ???
