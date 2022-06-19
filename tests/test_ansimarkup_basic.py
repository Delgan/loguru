import pytest
from colorama import Back, Fore, Style

from .conftest import parse


@pytest.mark.parametrize(
    "text, expected",
    [
        ("<bold>1</bold>", Style.BRIGHT + "1" + Style.RESET_ALL),
        ("<dim>1</dim>", Style.DIM + "1" + Style.RESET_ALL),
        ("<normal>1</normal>", Style.NORMAL + "1" + Style.RESET_ALL),
        ("<b>1</b>", Style.BRIGHT + "1" + Style.RESET_ALL),
        ("<d>1</d>", Style.DIM + "1" + Style.RESET_ALL),
        ("<n>1</n>", Style.NORMAL + "1" + Style.RESET_ALL),
    ],
)
def test_styles(text, expected):
    assert parse(text, strip=False) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("<RED>1</RED>", Back.RED + "1" + Style.RESET_ALL),
        ("<R>1</R>", Back.RED + "1" + Style.RESET_ALL),
        ("<LIGHT-GREEN>1</LIGHT-GREEN>", Back.LIGHTGREEN_EX + "1" + Style.RESET_ALL),
        ("<LG>1</LG>", Back.LIGHTGREEN_EX + "1" + Style.RESET_ALL),
    ],
)
def test_background_colors(text, expected):
    assert parse(text, strip=False) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("<yellow>1</yellow>", Fore.YELLOW + "1" + Style.RESET_ALL),
        ("<y>1</y>", Fore.YELLOW + "1" + Style.RESET_ALL),
        ("<light-white>1</light-white>", Fore.LIGHTWHITE_EX + "1" + Style.RESET_ALL),
        ("<lw>1</lw>", Fore.LIGHTWHITE_EX + "1" + Style.RESET_ALL),
    ],
)
def test_foreground_colors(text, expected):
    assert parse(text, strip=False) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "<b>1</b><d>2</d>",
            Style.BRIGHT + "1" + Style.RESET_ALL + Style.DIM + "2" + Style.RESET_ALL,
        ),
        (
            "<b>1</b>2<d>3</d>",
            Style.BRIGHT + "1" + Style.RESET_ALL + "2" + Style.DIM + "3" + Style.RESET_ALL,
        ),
        (
            "0<b>1<d>2</d>3</b>4",
            "0"
            + Style.BRIGHT
            + "1"
            + Style.DIM
            + "2"
            + Style.RESET_ALL
            + Style.BRIGHT
            + "3"
            + Style.RESET_ALL
            + "4",
        ),
        (
            "<d>0<b>1<d>2</d>3</b>4</d>",
            Style.DIM
            + "0"
            + Style.BRIGHT
            + "1"
            + Style.DIM
            + "2"
            + Style.RESET_ALL
            + Style.DIM
            + Style.BRIGHT
            + "3"
            + Style.RESET_ALL
            + Style.DIM
            + "4"
            + Style.RESET_ALL,
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
        ("<b>", Style.BRIGHT),
        ("<Y><b></b>", Back.YELLOW + Style.BRIGHT + Style.RESET_ALL + Back.YELLOW),
        ("<b><b></b>", Style.BRIGHT + Style.BRIGHT + Style.RESET_ALL + Style.BRIGHT),
    ],
)
def test_permissive_parsing(text, expected):
    assert parse(text, strip=False, strict=False) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("<red>foo</>", Fore.RED + "foo" + Style.RESET_ALL),
        (
            "<green><bold>bar</></green>",
            Fore.GREEN + Style.BRIGHT + "bar" + Style.RESET_ALL + Fore.GREEN + Style.RESET_ALL,
        ),
        (
            "a<yellow>b<b>c</>d</>e",
            "a"
            + Fore.YELLOW
            + "b"
            + Style.BRIGHT
            + "c"
            + Style.RESET_ALL
            + Fore.YELLOW
            + "d"
            + Style.RESET_ALL
            + "e",
        ),
    ],
)
def test_autoclose(text, expected):
    assert parse(text, strip=False) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        (r"<red>foo\</red>bar</red>", Fore.RED + "foo</red>bar" + Style.RESET_ALL),
        (r"<red>foo\<red>bar</red>", Fore.RED + "foo<red>bar" + Style.RESET_ALL),
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
