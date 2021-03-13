import pytest
from colorama import Back as B
from colorama import Fore as F
from colorama import Style as S

from .conftest import parse


@pytest.mark.parametrize(
    "text, expected",
    [
        ("<bg red>1</bg red>", B.RED + "1" + S.RESET_ALL),
        ("<bg BLACK>1</bg BLACK>", B.BLACK + "1" + S.RESET_ALL),
        ("<bg light-green>1</bg light-green>", B.LIGHTGREEN_EX + "1" + S.RESET_ALL),
        ("<bg LIGHT-MAGENTA>1</bg LIGHT-MAGENTA>", B.LIGHTMAGENTA_EX + "1" + S.RESET_ALL),
    ],
)
def test_background_colors(text, expected):
    assert parse(text, strip=False) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("<fg yellow>1</fg yellow>", F.YELLOW + "1" + S.RESET_ALL),
        ("<fg BLUE>1</fg BLUE>", F.BLUE + "1" + S.RESET_ALL),
        ("<fg light-white>1</fg light-white>", F.LIGHTWHITE_EX + "1" + S.RESET_ALL),
        ("<fg LIGHT-CYAN>1</fg LIGHT-CYAN>", F.LIGHTCYAN_EX + "1" + S.RESET_ALL),
    ],
)
def test_foreground_colors(text, expected):
    assert parse(text, strip=False) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("<fg #ff0000>1</fg #ff0000>", "\x1b[38;2;255;0;0m" "1" + S.RESET_ALL),
        ("<bg #00A000>1</bg #00A000>", "\x1b[48;2;0;160;0m" "1" + S.RESET_ALL),
        ("<fg #F12>1</fg #F12>", "\x1b[38;2;241;47;18m" "1" + S.RESET_ALL),
    ],
)
def test_8bit_colors(text, expected):
    assert parse(text, strip=False) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("<fg #ff0000>1</fg #ff0000>", "\x1b[38;2;255;0;0m" "1" + S.RESET_ALL),
        ("<bg #00A000>1</bg #00A000>", "\x1b[48;2;0;160;0m" "1" + S.RESET_ALL),
        ("<fg #F12>1</fg #F12>", "\x1b[38;2;241;47;18m" "1" + S.RESET_ALL),
        ("<bg #BEE>1</bg #BEE>", "\x1b[48;2;190;235;238m" "1" + S.RESET_ALL),
    ],
)
def test_hex_colors(text, expected):
    assert parse(text, strip=False) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("<fg 200>1</fg 200>", "\x1b[38;5;200m" "1" + S.RESET_ALL),
        ("<bg 49>1</bg 49>", "\x1b[48;5;49m" "1" + S.RESET_ALL),
    ],
)
def test_rgb_colors(text, expected):
    assert parse(text, strip=False) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "<red><b><bg #00A000>1</bg #00A000></b></red>",
            F.RED + S.BRIGHT + "\x1b[48;2;0;160;0m"
            "1" + S.RESET_ALL + F.RED + S.BRIGHT + S.RESET_ALL + F.RED + S.RESET_ALL,
        ),
        (
            "<bg 100><fg 200>1</fg 200></bg 100>",
            "\x1b[48;5;100m" "\x1b[38;5;200m" "1" "\x1b[0m" "\x1b[48;5;100m" "\x1b[0m",
        ),
        (
            "<bg #00a000><fg #FF0000>1</fg #FF0000></bg #00a000>",
            "\x1b[48;2;0;160;0m" "\x1b[38;2;255;0;0m" "1" "\x1b[0m" "\x1b[48;2;0;160;0m" "\x1b[0m",
        ),
        (
            "<bg 0,160,0><fg 255,0,0>1</fg 255,0,0></bg 0,160,0>",
            "\x1b[48;2;0;160;0m" "\x1b[38;2;255;0;0m" "1" "\x1b[0m" "\x1b[48;2;0;160;0m" "\x1b[0m",
        ),
    ],
)
def test_nested(text, expected):
    assert parse(text, strip=False) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("<r>2 > 1</r>", F.RED + "2 > 1" + S.RESET_ALL),
        ("<r>1 < 2</r>", F.RED + "1 < 2" + S.RESET_ALL),
        ("<r>1 </ 2</r>", F.RED + "1 </ 2" + S.RESET_ALL),
        ("{: <10}<r>1</r>", "{: <10}" + F.RED + "1" + S.RESET_ALL),
        ("{: </10}<r>1</r>", "{: </10}" + F.RED + "1" + S.RESET_ALL),
        ("<r>1</r>{: >10}", F.RED + "1" + S.RESET_ALL + "{: >10}"),
        ("<1<r>2</r>3>", "<1" + F.RED + "2" + S.RESET_ALL + "3>"),
        ("</1<r>2</r>3>", "</1" + F.RED + "2" + S.RESET_ALL + "3>"),
        ("<1<r>2 < 3</r>4>", "<1" + F.RED + "2 < 3" + S.RESET_ALL + "4>"),
        ("<1<r>2 </ 3</r>4>", "<1" + F.RED + "2 </ 3" + S.RESET_ALL + "4>"),
        ("<1<r>3 > 2</r>4>", "<1" + F.RED + "3 > 2" + S.RESET_ALL + "4>"),
    ],
)
def test_tricky_parse(text, expected):
    assert parse(text, strip=False) == expected


@pytest.mark.parametrize(
    "text",
    [
        "<fg light-blue2>1</fg light-blue2>",
        "<bg ,red>1</bg ,red>",
        "<bg red,>1</bg red,>",
        "<bg a,z>1</bg a,z>",
        "<bg blue,yelllow>1</bg blue,yelllow>",
        "<>1</>",
        "<,>1</,>",
        "<z,z>1</z,z>",
        "<z,z,z>1</z,z,z>",
        "<fg>1</fg>",
    ],
)
@pytest.mark.parametrize("strip", [True, False])
def test_invalid_color(text, strip):
    with pytest.raises(ValueError):
        parse(text, strip=strip)


@pytest.mark.parametrize(
    "text",
    [
        "<fg #>1</fg #>",
        "<bg #12>1</bg #12>",
        "<fg #1234567>1</fg #1234567>",
        "<bg #E7G>1</bg #E7G>",
        "fg #F2D1GZ>1</fg #F2D1GZ>",
    ],
)
@pytest.mark.parametrize("strip", [True, False])
def test_invalid_hex(text, strip):
    with pytest.raises(ValueError):
        parse(text, strip=strip)


@pytest.mark.parametrize("text", ["<fg 256>1</fg 256>", "<bg 2222>1</bg 2222>", "<bg -1>1</bg -1>"])
@pytest.mark.parametrize("strip", [True, False])
def test_invalid_8bit(text, strip):
    with pytest.raises(ValueError):
        parse(text, strip=strip)


@pytest.mark.parametrize(
    "text",
    [
        "<fg 1,2,>1</fg 1,2,>",
        "<bg ,>1</bg ,>",
        "<fg ,,>1</fg ,,>",
        "<fg 256,120,120>1</fg 256,120,120>",
        "<bg 1,2,3,4>1</bg 1,2,3,4>",
    ],
)
@pytest.mark.parametrize("strip", [True, False])
def test_invalid_rgb(text, strip):
    with pytest.raises(ValueError):
        parse(text, strip=strip)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("<fg #ff0000>foobar</fg #ff0000>", "foobar"),
        ("<fg 55>baz</fg 55>", "baz"),
        ("<bg 23,12,12>bar</bg 23,12,12>", "bar"),
    ],
)
def test_strip(text, expected):
    assert parse(text, strip=True) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("<r>2 > 1</r>", "2 > 1"),
        ("<r>1 < 2</r>", "1 < 2"),
        ("<r>1 </ 2</r>", "1 </ 2"),
        ("{: <10}<r>1</r>", "{: <10}1"),
        ("{: </10}<r>1</r>", "{: </10}1"),
        ("<r>1</r>{: >10}", "1{: >10}"),
        ("<1<r>2</r>3>", "<123>"),
        ("</1<r>2</r>3>", "</123>"),
        ("<1<r>2 < 3</r>4>", "<12 < 34>"),
        ("<1<r>2 </ 3</r>4>", "<12 </ 34>"),
        ("<1<r>3 > 2</r>4>", "<13 > 24>"),
    ],
)
def test_tricky_strip(text, expected):
    assert parse(text, strip=True) == expected
