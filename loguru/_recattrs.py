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


class RecordException(namedtuple("RecordException", ("type", "value", "traceback"))):
    def __repr__(self):
        return "(type=%r, value=%r, traceback=%r)" % (self.type, self.value, self.traceback)

    def __reduce__(self):
        try:
            pickled_value = pickle.dumps(self.value)
        except pickle.PickleError:
            return (RecordException, (self.type, None, None))
        else:
            return (RecordException._from_pickled_value, (self.type, pickled_value, None))

    @classmethod
    def _from_pickled_value(cls, type_, pickled_value, traceback_):
        try:
            value = pickle.loads(pickled_value)
        except pickle.PickleError:
            return cls(type_, None, traceback_)
        else:
            return cls(type_, value, traceback_)
