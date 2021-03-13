import pytest
from colorama import Back as B
from colorama import Fore as F
from colorama import Style as S

from .conftest import parse


@pytest.mark.parametrize(
    "text, expected",
    [
        ("<bold>1</bold>", S.BRIGHT + "1" + S.RESET_ALL),
        ("<dim>1</dim>", S.DIM + "1" + S.RESET_ALL),
        ("<normal>1</normal>", S.NORMAL + "1" + S.RESET_ALL),
        ("<b>1</b>", S.BRIGHT + "1" + S.RESET_ALL),
        ("<d>1</d>", S.DIM + "1" + S.RESET_ALL),
        ("<n>1</n>", S.NORMAL + "1" + S.RESET_ALL),
    ],
)
def test_styles(text, expected):
    assert parse(text, strip=False) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("<RED>1</RED>", B.RED + "1" + S.RESET_ALL),
        ("<R>1</R>", B.RED + "1" + S.RESET_ALL),
        ("<LIGHT-GREEN>1</LIGHT-GREEN>", B.LIGHTGREEN_EX + "1" + S.RESET_ALL),
        ("<LG>1</LG>", B.LIGHTGREEN_EX + "1" + S.RESET_ALL),
    ],
)
def test_background_colors(text, expected):
    assert parse(text, strip=False) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("<yellow>1</yellow>", F.YELLOW + "1" + S.RESET_ALL),
        ("<y>1</y>", F.YELLOW + "1" + S.RESET_ALL),
        ("<light-white>1</light-white>", F.LIGHTWHITE_EX + "1" + S.RESET_ALL),
        ("<lw>1</lw>", F.LIGHTWHITE_EX + "1" + S.RESET_ALL),
    ],
)
def test_foreground_colors(text, expected):
    assert parse(text, strip=False) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("<b>1</b><d>2</d>", S.BRIGHT + "1" + S.RESET_ALL + S.DIM + "2" + S.RESET_ALL),
        ("<b>1</b>2<d>3</d>", S.BRIGHT + "1" + S.RESET_ALL + "2" + S.DIM + "3" + S.RESET_ALL),
        (
            "0<b>1<d>2</d>3</b>4",
            "0" + S.BRIGHT + "1" + S.DIM + "2" + S.RESET_ALL + S.BRIGHT + "3" + S.RESET_ALL + "4",
        ),
        (
            "<d>0<b>1<d>2</d>3</b>4</d>",
            S.DIM
            + "0"
            + S.BRIGHT
            + "1"
            + S.DIM
            + "2"
            + S.RESET_ALL
            + S.DIM
            + S.BRIGHT
            + "3"
            + S.RESET_ALL
            + S.DIM
            + "4"
            + S.RESET_ALL,
        ),
    ],
)
def test_nested(text, expected):
    assert parse(text, strip=False) == expected


@pytest.mark.parametrize("text", ["<b>", "<Y><b></b>", "<b><b></b>"])
def test_strict_parsing(text):
    with pytest.raises(ValueError):
        parse(text, strip=False)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("<b>", S.BRIGHT),
        ("<Y><b></b>", B.YELLOW + S.BRIGHT + S.RESET_ALL + B.YELLOW),
        ("<b><b></b>", S.BRIGHT + S.BRIGHT + S.RESET_ALL + S.BRIGHT),
    ],
)
def test_permissive_parsing(text, expected):
    assert parse(text, strip=False, strict=False) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("<red>foo</>", F.RED + "foo" + S.RESET_ALL),
        (
            "<green><bold>bar</></green>",
            F.GREEN + S.BRIGHT + "bar" + S.RESET_ALL + F.GREEN + S.RESET_ALL,
        ),
        (
            "a<yellow>b<b>c</>d</>e",
            "a"
            + F.YELLOW
            + "b"
            + S.BRIGHT
            + "c"
            + S.RESET_ALL
            + F.YELLOW
            + "d"
            + S.RESET_ALL
            + "e",
        ),
    ],
)
def test_autoclose(text, expected):
    assert parse(text, strip=False) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        (r"<red>foo\</red>bar</red>", F.RED + "foo</red>bar" + S.RESET_ALL),
        (r"<red>foo\<red>bar</red>", F.RED + "foo<red>bar" + S.RESET_ALL),
        (r"\<red>\</red>", "<red></red>"),
        (r"foo\</>bar\</>baz", "foo</>bar</>baz"),
    ],
)
def test_escaping(text, expected):
    assert parse(text, strip=False) == expected


@pytest.mark.parametrize(
    "text",
    [
        "<b>1</d>",
        "</b>",
        "<b>1</b></b>",
        "<red><b>1</b></b></red>",
        "<tag>1</b>",
        "</>",
        "<red><green>X</></green>",
    ],
)
@pytest.mark.parametrize("strip", [True, False])
def test_mismatched_error(text, strip):
    with pytest.raises(ValueError):
        parse(text, strip=strip)


@pytest.mark.parametrize(
    "text", ["<r><Y>1</r>2</Y>", "<r><r><Y>1</r>2</Y></r>", "<r><Y><r></r></r></Y>"]
)
@pytest.mark.parametrize("strip", [True, False])
def test_unbalanced_error(text, strip):
    with pytest.raises(ValueError):
        parse(text, strip=strip)


@pytest.mark.parametrize("text", ["<b>", "<Y><b></b>", "<b><b></b>", "<fg red>1<fg red>"])
@pytest.mark.parametrize("strip", [True, False])
def test_unclosed_error(text, strip):
    with pytest.raises(ValueError):
        parse(text, strip=strip)


@pytest.mark.parametrize(
    "text",
    [
        "<foo>bar</foo>",
        "<Green>foobar</Green>",
        "<green>foo</bar>",
        "<bar>foo</green>",
        "<b>1</b><tag>2</tag>",
        "<tag>1</tag><b>2</b>",
        "<b>1</b><tag>2</tag><b>3</b>",
        "<tag>1</tag><b>2</b><tag>3</tag>",
        "<b><tag>1</tag></b>",
        "<tag><b>1</b></tag>",
        "<b></b><tag>1</tag>",
        "<tag>1</tag><b></b>",
    ],
)
@pytest.mark.parametrize("strip", [True, False])
def test_invalid_color(text, strip):
    with pytest.raises(ValueError):
        parse(text, strip=strip)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("<red>foo</red>", "foo"),
        ("<BLACK>bar</BLACK>", "bar"),
        ("<b>baz</b>", "baz"),
        ("<b>1</b>2<d>3</d>", "123"),
        ("<red>foo</>", "foo"),
    ],
)
def test_strip(text, expected):
    assert parse(text, strip=True) == expected
