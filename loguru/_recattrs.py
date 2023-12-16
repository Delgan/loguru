import pickle
from collections import namedtuple


class RecordLevel:
    __slots__ = ("name", "no", "icon")

    def __init__(self, name, no, icon):
        self.name = name
        self.no = no
        self.icon = icon

    def __repr__(self):
        return "(name=%r, no=%r, icon=%r)" % (self.name, self.no, self.icon)

    def __format__(self, spec):
        return self.name.__format__(spec)


class RecordFile:
    __slots__ = ("name", "path")

    def __init__(self, name, path):
        self.name = name
        self.path = path

    def __repr__(self):
        return "(name=%r, path=%r)" % (self.name, self.path)

    def __format__(self, spec):
        return self.name.__format__(spec)


class RecordThread:
    __slots__ = ("id", "name")

    def __init__(self, id_, name):
        self.id = id_
        self.name = name

    def __repr__(self):
        return "(id=%r, name=%r)" % (self.id, self.name)

    def __format__(self, spec):
        return self.id.__format__(spec)


class RecordProcess:
    __slots__ = ("id", "name")

    def __init__(self, id_, name):
        self.id = id_
        self.name = name

    def __repr__(self):
        return "(id=%r, name=%r)" % (self.id, self.name)

    def __format__(self, spec):
        return self.id.__format__(spec)


class RecordException(namedtuple("RecordException", ("type", "value", "traceback", "formatted_traceback"))):
    def __repr__(self):
        return "(type=%r, value=%r, traceback=%r, formatted_traceback=%r)" % (self.type, self.value, self.traceback, self.formatted_traceback)

    def __reduce__(self):
        # The traceback is not picklable, therefore it needs to be removed. Additionally, there's a
        # possibility that the exception value is not picklable either. In such cases, we also need
        # to remove it. This is done for user convenience, aiming to prevent error logging caused by
        # custom exceptions from third-party libraries. If the serialization succeeds, we can reuse
        # the pickled value later for optimization (so that it's not pickled twice). It's important
        # to note that custom exceptions might not necessarily raise a PickleError, hence the
        # generic Exception catch.
        pickled_value_success = True
        try:
            pickled_value = pickle.dumps(self.value)
        except Exception:
            pickled_value_success = False

        pickled_formatted_traceback_success = True
        try:
            pickled_formatted_traceback = pickle.dumps(self.formatted_traceback)
        except Exception:
            pickled_formatted_traceback_success = False

        if pickled_value_success and pickled_formatted_traceback_success:
            return (RecordException._from_pickled, (self.type, pickled_value, None, pickled_formatted_traceback))
        elif pickled_value_success:
            return (RecordException._from_pickled, (self.type, pickled_value, None, None))
        elif pickled_formatted_traceback_success:
            return (RecordException._from_pickled, (self.type, None, None, pickled_formatted_traceback))
        return (RecordException, (self.type, None, None, None))

    @classmethod
    def _from_pickled(cls, type_, pickled_value, traceback_, pickled_formatted_traceback_):
        unpickled_value = None
        if pickled_value:
            try:
                # It's safe to use "pickle.loads()" in this case because the pickled value is generated
                # by the same code and is not coming from an untrusted source.
                unpickled_value = pickle.loads(pickled_value)
            except Exception:
                pass

        unpickled_formatted_traceback_ = None
        if pickled_formatted_traceback_:
            try:
                # It's safe to use "pickle.loads()" in this case because the pickled value is generated
                # by the same code and is not coming from an untrusted source.
                unpickled_formatted_traceback_ = pickle.loads(pickled_formatted_traceback_)
            except Exception:
                pass

        return cls(type_, unpickled_value, traceback_, unpickled_formatted_traceback_)
