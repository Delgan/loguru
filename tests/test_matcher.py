import pytest
from loguru import parser
import re

string = "10 + 5 = Fifteen"
matcher = parser.matcher(string)


def test_search():
    pattern = "[A-Z][a-z]+"
    search = matcher.search(pattern)
    assert search.group() == re.search(pattern, string).group()

def test_match():
    pattern = "^\d+ \+ \d+ = \w+$"
    match = matcher.match(pattern)
    assert match.group() == re.match(pattern, string).group()

def test_fullmatch():
    pattern = "\d+ \+ \d+ = \w+"
    fullmatch = matcher.fullmatch(pattern)
    assert fullmatch.group() == re.fullmatch(pattern, string).group()

def test_split():
    pattern = "[\w\d]+"
    split = matcher.split(pattern)
    assert split == re.split(pattern, string)

def test_findall():
    pattern = "\d+"
    findall = matcher.findall(pattern)
    assert findall == re.findall(pattern, string)

def test_finditer():
    pattern = "(\d+)"
    finditer = matcher.finditer(pattern)
    assert [f.group() for f in finditer] == [f.group() for f in re.finditer(pattern, string)]

def test_sub():
    pattern, repl = "\+", "plus"
    sub = matcher.sub(pattern, repl)
    assert sub == re.sub(pattern, repl, string)

def test_subn():
    pattern, repl = "=", "equals"
    subn = matcher.subn(pattern, repl)
    assert subn == re.subn(pattern, repl, string)

def test_last_match():
    matcher = parser.matcher(string)
    assert matcher.last_match is None

    m = matcher.match("^\d+ \+ \d+ = \w+$")
    assert m is matcher.last_match is not None

    m = matcher.fullmatch("\d+ \+ \d+ = \w+")
    assert m is matcher.last_match is not None

    m = matcher.search("[A-Z][a-z]+")
    assert m is matcher.last_match is not None

    m = matcher.match("Nope")
    assert m is matcher.last_match is None

def test_match_getitem():
    matcher.match("(\d+) \+ (\d+) = (?P<result>\w+)")
    assert matcher[1] == "10"
    assert matcher[2] == "5"
    assert matcher["result"] == "Fifteen"

def test_match_group():
    matcher.match("\d+")
    assert matcher.group() == "10"

    matcher.match("(\d+) \+ (\d+)")
    assert matcher.group(1, 2) == ("10", "5")

    matcher.match("\d+ \+ \d+ = (?P<result>.*)")
    assert matcher.group("result") == "Fifteen"

def test_match_groups():
    matcher.match("(\d+) \+ (\d+) = (\w+)")
    assert matcher.groups() == ("10", "5", "Fifteen")

def test_match_groupdict():
    matcher.match("\d+ (?P<plus>.) \d+ (?P<equal>.) \w+")
    assert matcher.groupdict() == dict(plus="+", equal="=")

def test_match_start_end_span():
    matcher.match("\d+")
    assert matcher.start() == 0
    assert matcher.end() == 2
    assert matcher.span() == (0, 2)

def test_match_attrs():
    pattern = ".* = (?P<num>[A-Z][a-z]+)"
    matcher.match(pattern)
    assert matcher.lastindex == 1
    assert matcher.lastgroup == "num"
    assert matcher.re == re.compile(pattern)
    assert matcher.string == string

def test_cascaded_if():
    m = parser.matcher("10 * 2 = TWENTY")

    if m.fullmatch("\d+"):
        res = False
    elif m.match("\d+ \* \d+ = (?P<res>twenty)"):
        res = False
    elif m.match("\d+ \* \d+ = (?P<res>twenty)", re.I):
        res = (m.groupdict() == dict(res="TWENTY"))
    else:
        res = False

    assert res
