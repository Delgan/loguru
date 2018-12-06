import re
from os import PathLike


class Parser:
    """An object to more easily parse generated logs.

    The |Parser| provide a set of handful methods likely to be used while parsing logs for
    post-processing.

    You should not instaniate a |Parser| by yourself, use ``from loguru import parser`` instead.

    .. |Parser| replace:: :class:`~loguru._parser.Parser`

    .. |dict| replace:: :class:`dict`
    .. |str| replace:: :class:`str`
    .. |int| replace:: :class:`int`
    .. |Path| replace:: :class:`pathlib.Path`
    .. |match.groupdict| replace:: :meth:`re.Match.groupdict()`

    .. |file-like object| replace:: ``file-like object``
    .. _file-like object: https://docs.python.org/3/glossary.html#term-file-object
    .. |re.Pattern| replace:: ``re.Pattern``
    .. _re.Pattern: https://docs.python.org/3/library/re.html#re-objects
    .. |re.Match| replace:: ``re.Match``
    .. _re.Match: https://docs.python.org/3/library/re.html#match-objects
    """

    @staticmethod
    def cast(_dict, **kwargs):
        """Convert values of a dict to others defined types.

        This is a convenient function used to cast dict values resulting from parsed logs from
        |str| to a more appropriate type.

        Parameters
        ----------
        _dict : |dict|
            The dict to which values type should be changed.
        **kwargs
            Mapping between keys of the input ``_dict`` and the function that should be used to
            convert the associated value.

        Returns
        -------
        :class:`dict`
            A copy of the input dictionnary with values converted to the appropriate type.

        Example
        -------
        >>> dico = {"some": "text", "num": "42", "date": "2018-09-12 22:23:24"}
        >>> parser.cast(dico, num=int, date=lambda t: datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
        {'some': 'text', 'num': 42, 'date': datetime.datetime(2018, 9, 12, 22, 23, 24)}
        """
        dict_ = _dict.copy()
        for key, converter in kwargs.items():
            if key in dict_:
                dict_[key] = converter(dict_[key])
        return dict_

    @staticmethod
    def parse(file, pattern, *, chunk=2 ** 16):
        """
        Parse raw logs to extract each entry as a |dict|.

        The logging format has to be specified as the regex ``pattern``, it will then be
        used to parse the ``file`` and retrieve each entries based on the named groups present
        in the regex.

        Parameters
        ----------
        file : |str|, |Path| or |file-like object|_
            The path of the log file to be parsed, or alternatively an already opened file object.
        pattern : |str| or |re.Pattern|_
            The regex to use for logs parsing, it should contain named groups which will be included
            in the returned dict.
        chunk : |int|, optional
            The number of bytes read while iterating through the logs, this avoid having to load the
            whole file in memory.

        Yields
        ------
        :class:`dict`
            The dict mapping regex named groups to matched values, as returned by |match.groupdict|.

        Examples
        --------
        >>> reg = r"(?P<lvl>[0-9]+): (?P<msg>.*)"    # If log format is "{level.no} - {message}"
        >>> for e in parser.parse("file.log", reg):  # A file line could be "10 - A debug message"
        ...     print(e)                             # => {'lvl': '10', 'msg': 'A debug message'}
        """
        if isinstance(file, (str, PathLike)):
            should_close = True
            fileobj = open(str(file))
        elif hasattr(file, "read") and callable(file.read):
            should_close = False
            fileobj = file
        else:
            raise ValueError(
                "Invalid file, it should be a string path or a file object, not: '%s'"
                % type(file).__name__
            )

        try:
            regex = re.compile(pattern)
        except TypeError:
            raise ValueError(
                "Invalid pattern, it should be a string or a compiled regex, not: '%s'"
                % type(pattern).__name__
            )

        matches = Parser._find_iter(fileobj, regex, chunk)

        for match in matches:
            yield match.groupdict()

        if should_close:
            fileobj.close()

    @staticmethod
    def _find_iter(fileobj, regex, chunk):
        buffer = fileobj.read(0)

        while 1:
            text = fileobj.read(chunk)
            buffer += text
            matches = list(regex.finditer(buffer))

            if not text:
                yield from matches
                break

            if len(matches) > 1:
                end = matches[-2].end()
                buffer = buffer[end:]
                yield from matches[:-1]
