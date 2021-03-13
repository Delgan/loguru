import copy

from loguru import logger


def print_(message):
    print(message, end="")


def test_add_sink_after_deepcopy(capsys):
    logger_ = copy.deepcopy(logger)

    logger_.add(print_, format="{message}", catch=False)

    logger_.info("A")
    logger.info("B")

    out, err = capsys.readouterr()
    assert out == "A\n"
    assert err == ""


def test_add_sink_before_deepcopy(capsys):
    logger.add(print_, format="{message}", catch=False)

    logger_ = copy.deepcopy(logger)

    logger_.info("A")
    logger.info("B")

    out, err = capsys.readouterr()
    assert out == "A\nB\n"
    assert err == ""


def test_remove_from_original(capsys):
    logger.add(print_, format="{message}", catch=False)

    logger_ = copy.deepcopy(logger)
    logger.remove()

    logger_.info("A")
    logger.info("B")

    out, err = capsys.readouterr()
    assert out == "A\n"
    assert err == ""


def test_remove_from_copy(capsys):
    logger.add(print_, format="{message}", catch=False)

    logger_ = copy.deepcopy(logger)
    logger_.remove()

    logger_.info("A")
    logger.info("B")

    out, err = capsys.readouterr()
    assert out == "B\n"
    assert err == ""
