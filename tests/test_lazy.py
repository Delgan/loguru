from loguru import logger


def test_lazy_value(writer):
    logger_bound = logger.bind(a=0)
    logger_bound.add(writer, format="{message}")
    logger_bound.info("hello {}", logger.lazy(str, 1))

    assert writer.read() == "hello 1\n"
