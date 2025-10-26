import inspect
import logging
import weakref

from ._asyncio_loop import get_running_loop, get_task_loop


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
        self._tasks = weakref.WeakSet()

    def write(self, message):
        """Asynchronously write a message.

        Parameters
        ----------
        message
            The message to write.
        """
        try:
            loop = self._loop or get_running_loop()
        except RuntimeError:
            return

        coroutine = self._function(message)
        task = loop.create_task(coroutine)

        def check_exception(future):
            if future.cancelled() or future.exception() is None:
                return
            if not self._error_interceptor.should_catch():
                raise future.exception()
            self._error_interceptor.print(message.record, exception=future.exception())

        task.add_done_callback(check_exception)
        self._tasks.add(task)

    def stop(self):
        """Cancel all pending tasks."""
        for task in self._tasks:
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
        return [self._complete_task(task) for task in self._tasks]

    async def _complete_task(self, task):
        """Complete a single task.

        Parameters
        ----------
        task
            The task to complete.
        """
        loop = get_running_loop()
        if get_task_loop(task) is not loop:
            return
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
        self._tasks = weakref.WeakSet()


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
