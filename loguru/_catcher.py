import functools
from inspect import isclass


class Catcher:

    def __init__(self, logger, exception=Exception, *, level="ERROR", reraise=False,
                       message="An error has been caught in function '{record[function]}', "
                               "process '{record[process].name}' ({record[process].id}), "
                               "thread '{record[thread].name}' ({record[thread].id}):"):
        self._logger = logger
        self._exception = exception
        self._level = level
        self._reraise = reraise
        self._message = message
        self._as_decorator = False

    def __enter__(self):
        pass

    def __exit__(self, type_, value, traceback_):
        if type_ is None:
            return

        if not issubclass(type_, self._exception):
            return False

        logger = self._logger

        if self._as_decorator:
            logger = logger.opt(record=True, lazy=logger._lazy, backframe=logger._backframe + 2)
            log = logger._make_log_function(self._level, True, True)
        else:
            logger = logger.opt(record=True, lazy=logger._lazy, backframe=logger._backframe + 1)
            log = logger._make_log_function(self._level, True, False)

        log(logger, self._message)

        return not self._reraise

    def __call__(self, *args, **kwargs):
        if args and callable(args[0]) and (not isclass(args[0]) or not issubclass(args[0], BaseException)):
            function, args = args[0], args[1:]

            if args or kwargs:
                catcher = Catcher(self._logger, *args, **kwargs)
            else:
                catcher = Catcher(self._logger,
                                  exception=self._exception,
                                  level=self._level,
                                  reraise=self._reraise,
                                  message=self._message)

            catcher._as_decorator = True

            @functools.wraps(function)
            def catch_wrapper(*args, **kwargs):
                with catcher:
                    function(*args, **kwargs)

            return catch_wrapper

        return Catcher(self._logger, *args, **kwargs)
