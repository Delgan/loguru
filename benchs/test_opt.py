from loguru import logger
import pytest


def opt_function(logger):
    for _ in range(1000):
        logger.opt()


@pytest.mark.benchmark(group="opt")
def test_opt(benchmark):
    logger.stop()

    benchmark(opt_function, logger)
