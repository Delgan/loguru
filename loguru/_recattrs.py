import pickle
from collections import namedtuple


class RecordLevel:
    """A class representing the logging level record with name, number and icon.

    Attributes
    ----------
    icon : str
        The icon representing the log level
    name : str
        The name of the log level
    no : int
        The numeric value of the log level
    """

    __slots__ = ("icon", "name", "no")

    def __init__(self, name, no, icon):
        """Initialize a RecordLevel instance.

        Parameters
        ----------
        name : str
            The name of the log level
        no : int
            The numeric value of the log level
        icon : str
            The icon representing the log level
        """
        self.name = name
        self.no = no
        self.icon = icon

    def __repr__(self):
        """Return string representation of RecordLevel.

        Returns
        -------
        str
            Formatted string with name, number and icon
        """
        return "(name=%r, no=%r, icon=%r)" % (self.name, self.no, self.icon)

    def __format__(self, spec):
        """Format the RecordLevel instance.

        Parameters
        ----------
        spec : str
            Format specification

        Returns
        -------
        str
            Formatted name according to specification
        """
        return self.name.__format__(spec)


class RecordFile:
    """A class representing a file record with name and path.

    Attributes
    ----------
    name : str
        The name of the file
    path : str
        The path to the file
    """

    __slots__ = ("name", "path")

    def __init__(self, name, path):
        """Initialize a RecordFile instance.

        Parameters
        ----------
        name : str
            The name of the file
        path : str
            The path to the file
        """
        self.name = name
        self.path = path

    def __repr__(self):
        """Return string representation of RecordFile.

        Returns
        -------
        str
            Formatted string with name and path
        """
        return "(name=%r, path=%r)" % (self.name, self.path)

    def __format__(self, spec):
        """Format the RecordFile instance.

        Parameters
        ----------
        spec : str
            Format specification

        Returns
        -------
        str
            Formatted name according to specification
        """
        return self.name.__format__(spec)


class RecordThread:
    """A class representing a thread record with ID and name.

    Attributes
    ----------
    id : int
        The thread ID
    name : str
        The thread name
    """

    __slots__ = ("id", "name")

    def __init__(self, id_, name):
        """Initialize a RecordThread instance.

        Parameters
        ----------
        id_ : int
            The thread ID
        name : str
            The thread name
        """
        self.id = id_
        self.name = name

    def __repr__(self):
        """Return string representation of RecordThread.

        Returns
        -------
        str
            Formatted string with id and name
        """
        return "(id=%r, name=%r)" % (self.id, self.name)

    def __format__(self, spec):
        """Format the RecordThread instance.

        Parameters
        ----------
        spec : str
            Format specification

        Returns
        -------
        str
            Formatted ID according to specification
        """
        return self.id.__format__(spec)


class RecordProcess:
    """A class representing a process record with ID and name.

    Attributes
    ----------
    id : int
        The process ID
    name : str
        The process name
    """

    __slots__ = ("id", "name")

    def __init__(self, id_, name):
        """Initialize a RecordProcess instance.

        Parameters
        ----------
        id_ : int
            The process ID
        name : str
            The process name
        """
        self.id = id_
        self.name = name

    def __repr__(self):
        """Return string representation of RecordProcess.

        Returns
        -------
        str
            Formatted string with id and name
        """
        return "(id=%r, name=%r)" % (self.id, self.name)

    def __format__(self, spec):
        """Format the RecordProcess instance.

        Parameters
        ----------
        spec : str
            Format specification

        Returns
        -------
        str
            Formatted ID according to specification
        """
        return self.id.__format__(spec)


class RecordException(
    namedtuple("RecordException", ("type", "value", "traceback"))  # noqa: PYI024
):
    """A class representing an exception record with type, value and traceback.

    Attributes
    ----------
    type
        The exception type
    value
        The exception value
    traceback
        The exception traceback
    """

    def __repr__(self):
        """Return string representation of RecordException.

        Returns
        -------
        str
            Formatted string with type, value and traceback
        """
        return "(type=%r, value=%r, traceback=%r)" % (self.type, self.value, self.traceback)

    def __reduce__(self):
        """Reduce the RecordException for pickling.

        This method handles pickling of the exception, managing cases where
        the exception value or traceback might not be picklable.

        Returns
        -------
        tuple
            A tuple containing class and initialization arguments
        """
        # The traceback is not picklable, therefore it needs to be removed. Additionally, there's a
        # possibility that the exception value is not picklable either. In such cases, we also need
        # to remove it. This is done for user convenience, aiming to prevent error logging caused by
        # custom exceptions from third-party libraries. If the serialization succeeds, we can reuse
        # the pickled value later for optimization (so that it's not pickled twice). It's important
        # to note that custom exceptions might not necessarily raise a PickleError, hence the
        # generic Exception catch.
        try:
            pickled_value = pickle.dumps(self.value)
        except Exception:
            return (RecordException, (self.type, None, None))
        else:
            return (RecordException._from_pickled_value, (self.type, pickled_value, None))

    @classmethod
    def _from_pickled_value(cls, type_, pickled_value, traceback_):
        """Create a RecordException instance from a pickled value.

        Parameters
        ----------
        type_
            The exception type
        pickled_value
            The pickled exception value
        traceback_
            The exception traceback

        Returns
        -------
        RecordException
            A new instance with unpickled value
        """
        try:
            # It's safe to use "pickle.loads()" in this case because the pickled value is generated
            # by the same code and is not coming from an untrusted source.
            value = pickle.loads(pickled_value)
        except Exception:
            return cls(type_, None, traceback_)
        else:
            return cls(type_, value, traceback_)
