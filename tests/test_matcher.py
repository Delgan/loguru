import pytest
from loguru import parser
import re

string = "10 + 5 = Fifteen"

@pytest.fixture
def matcher():
    yield parser.test(string)

def test_search(matcher):
    pattern = r"[A-Z][a-z]+"
    search = matcher.search(pattern)
    assert matcher.get().group() == search.group() == re.search(pattern, string).group()

def test_match(matcher):
    pattern = r"^\d+ \+ \d+ = \w+$"
    match = matcher.match(pattern)
    assert matcher.get().group() == match.group() == re.match(pattern, string).group()

def test_fullmatch(matcher):
    pattern = r"\d+ \+ \d+ = \w+"
    fullmatch = matcher.fullmatch(pattern)
    assert matcher.get().group() == fullmatch.group() == re.fullmatch(pattern, string).group()

def test_split(matcher):
    pattern = r"[\w\d]+"
    split = matcher.split(pattern)
    assert matcher.get() == split == re.split(pattern, string)

def test_findall(matcher):
    pattern = r"\d+"
    findall = matcher.findall(pattern)
    assert matcher.get() == findall == re.findall(pattern, string)

def test_finditer(matcher):
    pattern = r"(\d+)"
    expected = [f.group() for f in re.finditer(pattern, string)]
    finditer = matcher.finditer(pattern)
    assert [f.group() for f in finditer] == expected
    matcher.finditer(pattern)
    assert [f.group() for f in matcher.get()] == expected

def test_sub(matcher):
    pattern, repl = r"\+", "plus"
    sub = matcher.sub(pattern, repl)
    assert matcher.get() == sub == re.sub(pattern, repl, string)

def test_subn(matcher):
    pattern, repl = r"=", "equals"
    subn = matcher.subn(pattern, repl)
    assert matcher.get() == subn == re.subn(pattern, repl, string)

def test_match_getitem(matcher):
    matcher.match(r"(\d+) \+ (\d+) = (?P<result>\w+)")
    assert matcher.get()[1] == "10"
    assert matcher.get()[2] == "5"
    assert matcher.get()["result"] == "Fifteen"

def test_match_group(matcher):
    matcher.match(r"\d+")
    assert matcher.get().group() == "10"

    matcher.match(r"(\d+) \+ (\d+)")
    assert matcher.get().group(1, 2) == ("10", "5")

    matcher.match(r"\d+ \+ \d+ = (?P<result>.*)")
    assert matcher.get().group("result") == "Fifteen"

def test_match_groups(matcher):
    matcher.match(r"(\d+) \+ (\d+) = (\w+)")
    assert matcher.get().groups() == ("10", "5", "Fifteen")

def test_match_groupdict(matcher):
    matcher.match(r"\d+ (?P<plus>.) \d+ (?P<equal>.) \w+")
    assert matcher.get().groupdict() == dict(plus="+", equal="=")

def test_match_start_end_span(matcher):
    matcher.match(r"\d+")
    assert matcher.get().start() == 0
    assert matcher.get().end() == 2
    assert matcher.get().span() == (0, 2)

def test_match_attrs(matcher):
    pattern = r".* = (?P<num>[A-Z][a-z]+)"
    matcher.match(pattern)
    assert matcher.get().lastindex == 1
    assert matcher.get().lastgroup == "num"
    assert matcher.get().re == re.compile(pattern)
    assert matcher.get().string == string

def test_match_bool(matcher):
    matcher.match(r"nope")
    assert not bool(matcher.get())
    matcher.match(r".*")
    assert bool(matcher.get())

def test_get(matcher):
    assert matcher.get() is None

    m = matcher.match(r"^\d+ \+ \d+ = \w+$")
    assert m is matcher.get() is not None

    m = matcher.fullmatch(r"\d+ \+ \d+ = \w+")
    assert m is matcher.get() is not None

    m = matcher.search(r"[A-Z][a-z]+")
    assert m is matcher.get() is not None

    m = matcher.match(r"Nope")
    assert m is matcher.get() is None

def test_cascaded_if():
    m = parser.test("10 * 2 = TWENTY")

    if m.fullmatch(r"\d+"):
        res = False
    elif m.match(r"\d+ \* \d+ = (?P<res>twenty)"):
        res = False
    elif m.match(r"\d+ \* \d+ = (?P<res>twenty)", re.I):
        res = (m.get().groupdict() == dict(res="TWENTY"))
    else:
        res = False

    assert res
