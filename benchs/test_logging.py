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

@pytest.fixture(params=[0, 1, 10])
def nb_handlers(benchmark, request):
    benchmark.group = "logging - handlers x%d" % request.param
    return request.param

def test_standard_logging(benchmark, nb_handlers):
    logger = logging.getLogger(__name__)
    handler = PassHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.setLevel("INFO")
    logger.setLevel("INFO")

    for _ in range(nb_handlers):
        logger.addHandler(handler)

    benchmark(log_function, logger)

def test_loguru_logging(benchmark, nb_handlers):
    logger = loguru.logger
    logger.stop()

    for _ in range(nb_handlers):
        logger.start(PassHandler(), format="{message}", colored=False, level="INFO")

    benchmark(log_function, logger)
