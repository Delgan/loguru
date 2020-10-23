from loguru import logger


def test_patch_after_add(writer):
    logger.add(writer, format="{extra[a]} {message}")
    logger_patched = logger.patch(lambda r: r["extra"].update(a=0))
    logger_patched.debug("A")

    assert writer.read() == "0 A\n"


def test_patch_before_add(writer):
    logger_patched = logger.patch(lambda r: r["extra"].update(a=0))
    logger.add(writer, format="{extra[a]} {message}")
    logger_patched.debug("A")

    assert writer.read() == "0 A\n"


def test_add_using_patched(writer):
    logger.configure(patcher=lambda r: r["extra"].update(a=-1))
    logger_patched = logger.patch(lambda r: r["extra"].update(a=0))
    logger_patched.add(writer, format="{extra[a]} {message}")
    logger.debug("A")
    logger_patched.debug("B")

    assert writer.read() == "-1 A\n0 B\n"


def test_not_override_parent_logger(writer):
    logger_1 = logger.patch(lambda r: r["extra"].update(a="a"))
    logger_2 = logger_1.patch(lambda r: r["extra"].update(a="A"))
    logger.add(writer, format="{extra[a]} {message}")

    logger_1.debug("1")
    logger_2.debug("2")

    assert writer.read() == "a 1\nA 2\n"


def test_override_previous_patched(writer):
    logger.add(writer, format="{extra[x]} {message}")
    logger2 = logger.patch(lambda r: r["extra"].update(x=3))
    logger2.patch(lambda r: r["extra"].update(x=2)).debug("4")
    assert writer.read() == "2 4\n"


def test_no_conflict(writer):
    logger_ = logger.patch(lambda r: None)
    logger_2 = logger_.patch(lambda r: r["extra"].update(a=2))
    logger_3 = logger_.patch(lambda r: r["extra"].update(a=3))

    logger.add(writer, format="{extra[a]} {message}")

    logger_2.debug("222")
    logger_3.debug("333")

    assert writer.read() == "2 222\n3 333\n"


def test_override_configured(writer):
    logger.configure(patcher=lambda r: r["extra"].update(a=123, b=678))
    logger2 = logger.patch(lambda r: r["extra"].update(a=456))

    logger2.add(writer, format="{extra[a]} {extra[b]} {message}")

    logger2.debug("!")

    assert writer.read() == "456 678 !\n"
