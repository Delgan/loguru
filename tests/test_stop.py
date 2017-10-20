import sys

message = 'some message'
expected = message + '\n'

def test_stop_all(tmpdir, writer, capsys, logger):
    file = tmpdir.join("test.log")

    logger.debug("This shouldn't be printed.")

    logger.log_to(file.realpath(), format='{message}')
    logger.log_to(sys.stdout, format='{message}')
    logger.log_to(sys.stderr, format='{message}')
    logger.log_to(writer, format='{message}')

    logger.debug(message)

    logger.stop()

    logger.debug("This shouldn't be printed neither.")

    out, err = capsys.readouterr()

    assert file.read() == expected
    assert out == expected
    assert err == expected
    assert writer.read() == expected

def test_stop_count(logger, writer):
    n = logger.stop()
    assert n == 0

    n = logger.stop(42)
    assert n == 0

    i = logger.log_to(writer)
    n = logger.stop(i)
    assert n == 1

    logger.log_to(writer)
    logger.log_to(writer)
    n = logger.stop()
    assert n == 2

    n = logger.stop(0)
    assert n == 0
