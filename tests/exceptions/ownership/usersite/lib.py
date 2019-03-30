def divide(x, y):
    x / y


def divide_indirect(a, b):
    divide(a, b)


def callme(callback):
    callback()


def execute():
    exec("divide(1, 0)")


def syntaxerror():
    exec("foo =")


def assertionerror(x, y):
    assert x == y
