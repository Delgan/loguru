import sys
import traceback

from ._locks_machinery import create_error_lock


class ErrorInterceptor:
    def __init__(self, should_catch, handler_id):
        self._should_catch = should_catch
        self._handler_id = handler_id
        self._lock = create_error_lock()

    def should_catch(self):
        return self._should_catch

    def print(self, record=None, *, exception=None):
        if not sys.stderr:
            return

        # The Lock prevents concurrent writes to standard error. Also, it's registered into the
        # machinery to make sure no fork occurs while internal Lock of "sys.stderr" is acquired.
        with self._lock:
            if exception is None:
                type_, value, traceback_ = sys.exc_info()
            else:
                type_, value, traceback_ = (type(exception), exception, exception.__traceback__)

            try:
                sys.stderr.write("--- Logging error in Loguru Handler #%d ---\n" % self._handler_id)
                try:
                    record_repr = str(record)
                except Exception:
                    record_repr = "/!\\ Unprintable record /!\\"
                sys.stderr.write("Record was: %s\n" % record_repr)
                traceback.print_exception(type_, value, traceback_, None, sys.stderr)
                sys.stderr.write("--- End of logging error ---\n")
            except OSError:
                pass
            finally:
                del type_, value, traceback_

    def __getstate__(self):
        state = self.__dict__.copy()
        state["_lock"] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._lock = create_error_lock()
