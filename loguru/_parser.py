import re
from os import PathLike


class Parser:

    @staticmethod
    def cast(_dict, **kwargs):
        dict_ = _dict.copy()
        for key, converter in kwargs.items():
            if key in dict_:
                dict_[key] = converter(dict_[key])
        return dict_

    @staticmethod
    def parse(file, pattern, *, chunk=2**16):
        if isinstance(file, (str, PathLike)):
            should_close = True
            fileobj = open(str(file))
        elif hasattr(file, 'read') and callable(file.read):
            should_close = False
            fileobj = file
        else:
            raise ValueError("Invalid file, it should be a string path or a file object, not: '%s'" % type(file).__name__)

        try:
            regex = re.compile(pattern)
        except TypeError:
            raise ValueError("Invalid pattern, it should be a string or a compiled regex, not: '%s'" % type(pattern).__name__)

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
