from re import search, match, fullmatch, split, findall, finditer, sub, subn


class Matcher:

    def __init__(self, string):
        self.string = string
        self.last_match = None

    def __getattr__(self, attr):
        return getattr(self.last_match, attr)

    def __getitem__(self, g):
        return self.last_match[g]

    def search(self, pattern, flags=0):
        self.last_match = search(pattern, self.string, flags)
        return self.last_match

    def match(self, pattern, flags=0):
        self.last_match = match(pattern, self.string, flags)
        return self.last_match

    def fullmatch(self, pattern, flags=0):
        self.last_match = fullmatch(pattern, self.string, flags)
        return self.last_match

    def split(self, pattern, maxsplit=0, flags=0):
        return split(pattern, self.string, maxsplit, flags)

    def findall(self, pattern, flags=0):
        return findall(pattern, self.string, flags)

    def finditer(self, pattern, flags=0):
        return finditer(pattern, self.string, flags)

    def sub(self, pattern, repl, count=0, flags=0):
        return sub(pattern, repl, self.string, count, flags)

    def subn(self, pattern, repl, count=0, flags=0):
        return subn(pattern, repl, self.string, count, flags)
