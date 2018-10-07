from re import search, match, fullmatch, split, findall, finditer, sub, subn


class Matcher:

    def __init__(self, string):
        self.string = string
        self._result = None

    def get(self):
        return self._result

    def search(self, pattern, flags=0):
        self._result = search(pattern, self.string, flags)
        return self._result

    def match(self, pattern, flags=0):
        self._result = match(pattern, self.string, flags)
        return self._result

    def fullmatch(self, pattern, flags=0):
        self._result = fullmatch(pattern, self.string, flags)
        return self._result

    def split(self, pattern, maxsplit=0, flags=0):
        self._result = split(pattern, self.string, maxsplit, flags)
        return self._result

    def findall(self, pattern, flags=0):
        self._result = findall(pattern, self.string, flags)
        return self._result

    def finditer(self, pattern, flags=0):
        self._result = finditer(pattern, self.string, flags)
        return self._result

    def sub(self, pattern, repl, count=0, flags=0):
        self._result = sub(pattern, repl, self.string, count, flags)
        return self._result

    def subn(self, pattern, repl, count=0, flags=0):
        self._result = subn(pattern, repl, self.string, count, flags)
        return self._result
