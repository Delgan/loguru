from loguru import logger

# See "test_catch_exceptions.py" for extended testing


def test_diagnose(writer):
    logger.add(writer, format="{message}", diagnose=True)
    try:
        1 / 0
    except:
        logger.exception("")
    result_with = writer.read().strip()

    logger.remove()
    writer.clear()

    logger.add(writer, format="{message}", diagnose=False)
    try:
        1 / 0
    except:
        logger.exception("")
    result_without = writer.read().strip()

    assert len(result_with.splitlines()) > len(result_without.splitlines())
