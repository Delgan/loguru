import sys

message = 'some message'
expected = message + '\n'

def test_clear_all(tmpdir, writer, capsys, logger):
    file = tmpdir.join("test.log")

    logger.debug("This shouldn't be printed.")

    logger.log_to(file.realpath(), format='{message}')
    logger.log_to(sys.stdout, format='{message}')
    logger.log_to(sys.stderr, format='{message}')
    logger.log_to(writer, format='{message}')

    logger.debug(message)

    logger.clear()

    logger.debug("This shouldn't be printed neither.")

    out, err = capsys.readouterr()

    assert file.read() == expected
    assert out == expected
    assert err == expected
    assert writer.read() == expected

def test_clear_count(logger, writer):
    n = logger.clear()
    assert n == 0

    n = logger.clear(42)
    assert n == 0

    i = logger.log_to(writer)
    n = logger.clear(i)
    assert n == 1

    logger.log_to(writer)
    logger.log_to(writer)
    n = logger.clear()
    assert n == 2

    n = logger.clear(0)
    assert n == 0
