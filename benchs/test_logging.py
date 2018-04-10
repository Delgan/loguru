import logging
import loguru
import pytest


class PassHandler(logging.Handler):

    def emit(self, record):
        pass

    def write(self, record):
        pass

    flush = None

def log_function(logger):
    for _ in range(1000):
        logger.info("A message")


@pytest.mark.benchmark(group="logging")
def test_standard_logging(benchmark):
    logger = logging.getLogger(__name__)
    handler = PassHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.setLevel("INFO")
    logger.setLevel("INFO")
    logger.addHandler(handler)

    benchmark(log_function, logger)

@pytest.mark.benchmark(group="logging")
def test_loguru_logging(benchmark):
    logger = loguru.logger
    logger.stop()
    logger.start(PassHandler(), format="{message}", colored=False, level="INFO")

    benchmark(log_function, logger)
