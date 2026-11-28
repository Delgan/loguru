import asyncio
import concurrent.futures
import inspect
import logging
import weakref

from ._asyncio_loop import get_running_loop


class StreamSink:
    """A sink that writes log messages to a stream object.

    Parameters
    ----------
    stream
        A stream object that supports write operations.
    """

    def __init__(self, stream):
        self._stream = stream
        self._flushable = callable(getattr(stream, "flush", None))
        self._stoppable = callable(getattr(stream, "stop", None))
        self._completable = inspect.iscoroutinefunction(getattr(stream, "complete", None))

    def write(self, message):
        """Write a message to the stream.

        Parameters
        ----------
        message
            The message to write.
        """
        self._stream.write(message)
        if self._flushable:
            self._stream.flush()

    def stop(self):
        """Stop the stream if it supports the stop operation."""
        if self._stoppable:
            self._stream.stop()

    def tasks_to_complete(self):
        """Return list of tasks that need to be completed.

        Returns
        -------
        list
            List of tasks to complete.
        """
        if not self._completable:
            return []
        return [self._stream.complete()]


class StandardSink:
    """A sink that writes log messages using the standard logging module.

    Parameters
    ----------
    handler
        A logging handler instance.
    """

    def __init__(self, handler):
        self._handler = handler

    def write(self, message):
        """Write a message using the standard logging handler.

        Parameters
        ----------
        message
            The message to write.
        """
        if message.record["level"].no < self._handler.level:
            return
        raw_record = message.record
        message = str(message)
        exc = raw_record["exception"]
        record = logging.getLogger().makeRecord(
            raw_record["name"],
            raw_record["level"].no,
            raw_record["file"].path,
            raw_record["line"],
            message,
            (),
            (exc.type, exc.value, exc.traceback) if exc else None,
            raw_record["function"],
            {"extra": raw_record["extra"]},
        )

        # By default, the standard logging module will format the exception and assign it to the
        # "exc_text" attribute. Then, the formatted exception will be automatically appended to the
        # message when the record is formatted. This is a problem, because that would cause the
        # exception to be duplicated in the log message, since it's also formatted by Loguru. To
        # avoid this, we set "exc_text" to a simple newline character, which will end the message.
        if exc:
            record.exc_text = "\n"

        record.levelname = raw_record["level"].name

        record.thread = raw_record["thread"].id
        record.threadName = raw_record["thread"].name

        record.process = raw_record["process"].id
        record.processName = raw_record["process"].name

        self._handler.handle(record)

    def stop(self):
        """Close the logging handler."""
        self._handler.close()

    def tasks_to_complete(self):
        """Return list of tasks that need to be completed.

        Returns
        -------
        list
            Empty list as standard sink has no async tasks.
        """
        return []


class AsyncSink:
    """A sink that handles asynchronous logging operations.

    Parameters
    ----------
    function
        The async function to execute.
    loop
        The event loop to use.
    error_interceptor
        An interceptor for handling errors.
    """

    def __init__(self, function, loop, error_interceptor):
        self._function = function
        self._loop = loop
        self._error_interceptor = error_interceptor
        self._tasks = weakref.WeakKeyDictionary()

    def write(self, message):
        """Asynchronously write a message.

        Parameters
        ----------
        message
            The message to write.
        """
        try:
            running_loop = get_running_loop()
        except RuntimeError:
            running_loop = None

        loop = self._loop or running_loop
        if loop is None:
            return

        if loop.is_running() and running_loop is not loop:
            self._schedule_threadsafe(loop, message)
            return

        coroutine = self._function(message)
        task = loop.create_task(coroutine)
        task.add_done_callback(self._make_done_callback(message.record))
        self._tasks[task] = loop

    def _make_done_callback(self, record, future=None):
        """Create a completion callback that handles exceptions and resolves an optional future.

        Parameters
        ----------
        record
            The log record associated with the task.
        future
            Optional thread-safe future tracking completion of a cross-thread task.

        Returns
        -------
        callable
            Done callback for an ``asyncio.Task``.
        """

        def check_exception(task):
            if task.cancelled():
                if future is not None and not future.done():
                    future.cancel()
                return
            exc = task.exception()
            if future is not None and not future.done():
                future.set_result(None)
            if exc is None:
                return
            if not self._error_interceptor.should_catch():
                raise exc
            self._error_interceptor.print(record, exception=exc)

        return check_exception

    def _schedule_threadsafe(self, loop, message):
        """Schedule a coroutine task on an event loop running in another thread.

        Parameters
        ----------
        loop
            The target event loop.
        message
            The message to write.
        """
        future = concurrent.futures.Future()

        def create_task():
            if future.cancelled():
                return
            coroutine = None
            try:
                coroutine = self._function(message)
                task = loop.create_task(coroutine)
            except Exception as exc:
                if coroutine is not None:
                    coroutine.close()
                if not future.done():
                    future.set_result(None)
                if not self._error_interceptor.should_catch():
                    raise
                self._error_interceptor.print(message.record, exception=exc)
                return

            task.add_done_callback(self._make_done_callback(message.record, future=future))

            def cancel_task(f):
                if f.cancelled():
                    try:
                        loop.call_soon_threadsafe(task.cancel)
                    except RuntimeError:
                        pass

            future.add_done_callback(cancel_task)

        loop.call_soon_threadsafe(create_task)
        self._tasks[future] = loop

    def stop(self):
        """Cancel all pending tasks."""
        try:
            running_loop = get_running_loop()
        except RuntimeError:
            running_loop = None

        for task, loop in list(self._tasks.items()):
            if isinstance(task, concurrent.futures.Future):
                task.cancel()
            elif loop.is_running() and running_loop is not loop:
                try:
                    loop.call_soon_threadsafe(task.cancel)
                except RuntimeError:
                    pass
            else:
                task.cancel()

    def tasks_to_complete(self):
        """Return list of tasks that need to be completed.

        Returns
        -------
        list
            List of tasks to complete.
        """
        # To avoid errors due to "self._tasks" being mutated while iterated, the
        # "tasks_to_complete()" method must be protected by the same lock as "write()" (which
        # happens to be the handler lock). However, the tasks must not be awaited while the lock is
        # acquired as this could lead to a deadlock. Therefore, we first need to collect the tasks
        # to complete, then return them so that they can be awaited outside of the lock.
        return [self._complete_task(task, loop) for task, loop in self._tasks.items()]

    async def _complete_task(self, task, task_loop):
        """Complete a single task.

        Parameters
        ----------
        task
            The task to complete.
        task_loop
            The event loop associated with the task.
        """
        loop = get_running_loop()
        if task_loop is not loop:
            return
        if isinstance(task, concurrent.futures.Future):
            task = asyncio.wrap_future(task, loop=loop)
        try:
            await task
        except Exception:
            pass  # Handled in "check_exception()"

    def __getstate__(self):
        state = self.__dict__.copy()
        state["_tasks"] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._tasks = weakref.WeakKeyDictionary()


class CallableSink:
    """A sink that executes a callable function for each log message.

    Parameters
    ----------
    function
        The function to call for each message.
    """

    def __init__(self, function):
        self._function = function

    def write(self, message):
        """Write a message by calling the function.

        Parameters
        ----------
        message
            The message to pass to the function.
        """
        self._function(message)

    def stop(self):
        """Stop the sink (no-op for callable sink)."""
        pass

    def tasks_to_complete(self):
        """Return list of tasks that need to be completed.

        Returns
        -------
        list
            Empty list as callable sink has no tasks.
        """
        return []
