def test_record(logger, writer):
    logger.start(writer, format="{message}")

    logger.opt(record=True).debug("1")
    logger.opt(record=True).debug("2 {record[level]}")
    logger.opt(record=True).log(11, "3 {0} {a} {record[level].no}", 4, a=5)

    assert writer.read() == '1\n2 DEBUG\n3 4 5 11\n'

def test_exception(logger, writer):
    logger.start(writer, format="{level.name}: {message}")

    try:
        1 / 0
    except:
        logger.opt(exception=True).debug("Error {0} {record}", 1, record="test")

    lines = writer.read().strip().splitlines()

    assert lines[0] == "DEBUG: Error 1 test"
    assert lines[-1] == "ZeroDivisionError: division by zero"

def test_keep_extra(logger, writer):
    logger.extra['test'] = 123
    logger.start(writer, format='{extra[test]}')
    logger.opt().debug("")

    assert writer.read() == "123\n"

def test_keep_others(logger, writer):
    logger.start(writer, format='{message}')
    logger.opt(record=True).opt().debug("{record[level].name}")
    logger.debug("{record}", record=123)
    try:
        1 / 0
    except:
        logger.opt(record=True).opt(exception=True).debug("{record[level].no}")

    result = writer.read().strip()
    assert result.startswith("DEBUG\n123\n10\n")
    assert result.endswith("ZeroDivisionError: division by zero")

def test_before_bind(logger, writer):
    logger.start(writer, format='{message}')
    logger.opt(record=True).bind(key="value").info("{record[level]}")
    assert writer.read() == "INFO\n"
