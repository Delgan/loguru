import asyncio
import logging
import sys
import weakref

if sys.version_info >= (3, 7):

    def get_loop(task):
        return task.get_loop()


else:

    def get_loop(task):
        return task._loop


class StreamSink:
    def __init__(self, stream):
        self._stream = stream
        self._flushable = callable(getattr(stream, "flush", None))
        self._stoppable = callable(getattr(stream, "stop", None))
        self._completable = asyncio.iscoroutinefunction(getattr(stream, "complete", None))

    def write(self, message):
        self._stream.write(message)
        if self._flushable:
            self._stream.flush()

    def stop(self):
        if self._stoppable:
            self._stream.stop()

    async def complete(self):
        if self._completable:
            await self._stream.complete()


class StandardSink:
    def __init__(self, handler):
        self._handler = handler

    def write(self, message):
        record = message.record
        message = str(message)
        exc = record["exception"]
        record = logging.getLogger().makeRecord(
            record["name"],
            record["level"].no,
            record["file"].path,
            record["line"],
            message,
            (),
            (exc.type, exc.value, exc.traceback) if exc else None,
            record["function"],
            record["extra"],
        )
        if exc:
            record.exc_text = "\n"
        self._handler.handle(record)

    def stop(self):
        self._handler.close()

    async def complete(self):
        pass


class AsyncSink:
    def __init__(self, function, loop):
        self._function = function
        self._loop = loop
        self._tasks = weakref.WeakSet()

    def write(self, message):
        coro = self._function(message)
        loop = self._loop or asyncio.get_event_loop()
        task = loop.create_task(coro)
        self._tasks.add(task)

    def stop(self):
        for task in self._tasks:
            task.cancel()

    async def complete(self):
        loop = asyncio.get_event_loop()
        for task in self._tasks:
            if get_loop(task) is loop:
                await task

    def __getstate__(self):
        state = self.__dict__.copy()
        state["_tasks"] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._tasks = weakref.WeakSet()


class CallableSink:
    def __init__(self, function):
        self._function = function

    def write(self, message):
        self._function(message)

    def stop(self):
        pass

    async def complete(self):
        pass
