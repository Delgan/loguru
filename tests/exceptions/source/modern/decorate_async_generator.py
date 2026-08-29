from loguru import logger
import asyncio
import sys

logger.remove()

# We're truly only testing whether the tests succeed, we do not care about the formatting.
# These should be regular Pytest test cases, but that is not possible because the syntax is not valid in Python 3.5.
logger.add(lambda m: None, format="", diagnose=True, backtrace=True, colorize=True)

def test_decorate_async_generator():
    @logger.catch(reraise=True)
    async def generator(x, y):
        yield x
        yield y

    async def coro():
        out = []
        async for val in generator(1, 2):
            out.append(val)
        return out

    res = asyncio.run(coro())
    assert res == [1, 2]


def test_decorate_async_generator_with_error():
    @logger.catch(reraise=False)
    async def generator(x, y):
        yield x
        yield y
        raise ValueError

    async def coro():
        out = []
        async for val in generator(1, 2):
            out.append(val)
        return out

    res = asyncio.run(coro())
    assert res == [1, 2]

def test_decorate_async_generator_with_error_reraised():
    @logger.catch(reraise=True)
    async def generator(x, y):
        yield x
        yield y
        raise ValueError

    async def coro():
        out = []
        try:
            async for val in generator(1, 2):
                out.append(val)
        except ValueError:
            pass
        else:
            raise AssertionError("ValueError not raised")
        return out

    res = asyncio.run(coro())
    assert res == [1, 2]


def test_decorate_async_generator_then_async_send():
    @logger.catch
    async def generator(x, y):
        yield x
        yield y

    async def coro():
        gen = generator(1, 2)
        await gen.asend(None)
        await gen.asend(None)
        try:
            await gen.asend(None)
        except StopAsyncIteration:
            pass
        else:
            raise AssertionError("StopAsyncIteration not raised")

    asyncio.run(coro())


def test_decorate_async_generator_then_async_throw():
    @logger.catch
    async def generator(x, y):
        yield x
        yield y

    async def coro():
        gen = generator(1, 2)
        await gen.asend(None)
        try:
            await gen.athrow(ValueError)
        except ValueError:
            pass
        else:
            raise AssertionError("ValueError not raised")

    asyncio.run(coro())


def test_decorate_async_generator_athrow_with_new_error_reraised():
    logged = []
    logger.remove()
    logger.add(lambda message: logged.append(message.record["message"]), format="{message}", colorize=False)

    @logger.catch(reraise=True)
    async def generator():
        try:
            yield 1
        except TimeoutError:
            raise RuntimeError("boom")

    async def coro():
        gen = generator()
        await gen.asend(None)
        try:
            await gen.athrow(TimeoutError)
        except RuntimeError:
            pass
        else:
            raise AssertionError("RuntimeError not raised")

    asyncio.run(coro())
    assert len(logged) == 1

    logger.remove()
    logger.add(lambda m: None, format="", diagnose=True, backtrace=True, colorize=True)


test_decorate_async_generator()
test_decorate_async_generator_with_error()
test_decorate_async_generator_with_error_reraised()
test_decorate_async_generator_then_async_send()
test_decorate_async_generator_then_async_throw()
test_decorate_async_generator_athrow_with_new_error_reraised()

logger.add(sys.stderr, format="{message}")
logger.info("Done")
