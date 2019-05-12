import pytest
from colorama import Style as S, Fore as F, Back as B

from loguru._ansimarkup import AnsiMarkup


def p(text, *, strict=False):
    return AnsiMarkup(strip=False).feed(text, strict=strict)


def s(text, *, strict=False):
    return AnsiMarkup(strip=True).feed(text, strict=strict)


def test_flat():
    assert p("<b>1</b>") == p("<bold>1</bold>") == S.BRIGHT + "1" + S.RESET_ALL
    assert p("<d>1</d>") == p("<dim>1</dim>") == S.DIM + "1" + S.RESET_ALL

    assert p("<b>1</b><d>2</d>") == S.BRIGHT + "1" + S.RESET_ALL + S.DIM + "2" + S.RESET_ALL
    assert p("<b>1</b>2<d>3</d>") == S.BRIGHT + "1" + S.RESET_ALL + "2" + S.DIM + "3" + S.RESET_ALL


def test_flat_colors():
    assert (
        p("<r>1</r>") == p("<red>1</red>") == p("<fg red>1</fg red>") == F.RED + "1" + S.RESET_ALL
    )
    assert (
        p("<R>1</R>") == p("<RED>1</RED>") == p("<bg red>1</bg red>") == B.RED + "1" + S.RESET_ALL
    )

    assert (
        p("<r,y>1</r,y>") == p("<red,yellow>1</red,yellow>") == F.RED + B.YELLOW + "1" + S.RESET_ALL
    )
    assert (
        p("<b,r,y>1</b,r,y>")
        == p("<bold,red,yellow>1</bold,red,yellow>")
        == S.BRIGHT + F.RED + B.YELLOW + "1" + S.RESET_ALL
    )
    assert (
        p("<b,r,>1</b,r,>") == p("<bold,red,>1</bold,red,>") == S.BRIGHT + F.RED + "1" + S.RESET_ALL
    )

    assert p("<fg RED>1</fg RED>") == "<fg RED>1</fg RED>"
    assert p("<fg light-blue2>1</fg light-blue2>") == "<fg light-blue2>1</fg light-blue2>"

    assert p("<bg ,red>1</bg ,red>") == "<bg ,red>1</bg ,red>"
    assert p("<bg red,>1</bg red,>") == "<bg red,>1</bg red,>"
    assert p("<bg a,z>1</bg a,z>") == "<bg a,z>1</bg a,z>"
    assert p("<bg blue,yelllow>1</bg blue,yelllow>") == "<bg blue,yelllow>1</bg blue,yelllow>"
    assert p("<bg r, y>1</bg r, y>") == "<bg r, y>1</bg r, y>"

    assert p("<>1</>") == "<>1</>"
    assert p("</>1</>") == "</>1</>"
    assert p("<,>1</,>") == "<,>1</,>"
    assert p("<,,>1</,,>") == "<,,>1</,,>"
    assert p("<z,z>1</z,z>") == "<z,z>1</z,z>"
    assert p("<z,z,z>1</z,z,z>") == "<z,z,z>1</z,z,z>"

    assert p("<red,RED>1</red,RED>") == "<red,RED>1</red,RED>"
    assert p("<bold,red>1</bold,red>") == "<bold,red>1</bold,red>"
    assert p("<b,red,RED>1</b,red,RED>") == "<b,red,RED>1</b,red,RED>"
    assert p("<b,red,bold>1</b,red,bold>") == "<b,red,bold>1</b,red,bold>"
    assert p("<b,,>1</b,,>") == "<b,,>1</b,,>"
    assert p("<b,a,>1</b,a,>") == "<b,a,>1</b,a,>"
    assert p("<b,,z>1</b,,z>") == "<b,,z>1</b,,z>"


def test_xterm_color():
    assert p("<fg 200>1</fg 200>") == "\x1b[38;5;200m" "1" "\x1b[0m"
    assert p("<bg 100><fg 200>1") == "\x1b[48;5;100m" "\x1b[38;5;200m" "1"

    assert p("<fg 256>1") == "<fg 256>1"
    assert p("<bg 256>1</bg 256>") == "<bg 256>1</bg 256>"
    assert p("<bg 12 >1</bg 12 >") == "<bg 12 >1</bg 12 >"
    assert p("<bg 2222>1</bg 2222>") == "<bg 2222>1</bg 2222>"


def test_xterm_hex():
    assert p("<fg #ff0000>1") == p("<fg #FF0000>1") == "\x1b[38;2;255;0;0m" "1"
    assert p("<bg #00A000><fg #ff0000>1") == "\x1b[48;2;0;160;0m" "\x1b[38;2;255;0;0m" "1"
    assert (
        p("<fg #F12>1</fg #F12>")
        == p("<fg #F12F12>1</fg #F12F12>")
        == "\x1b[38;2;241;47;18m" + "1" + S.RESET_ALL
    )

    assert p("<fg #>1</fg #>") == "<fg #>1</fg #>"
    assert p("<bg #12>1</bg #12>") == "<bg #12>1</bg #12>"
    assert p("<fg #1234567>1</fg #1234567>") == "<fg #1234567>1</fg #1234567>"
    assert p("<bg #E7G>1</bg #E7G>") == "<bg #E7G>1</bg #E7G>"
    assert p("<fg #F2D1GZ>1</fg #F2D1GZ>") == "<fg #F2D1GZ>1</fg #F2D1GZ>"


def test_xterm_rgb():
    assert p("<fg 255,0,0>1") == p("<fg #ff0000>1") == "\x1b[38;2;255;0;0m" "1"
    assert (
        p("<bg 0,160,0><fg 255,0,0>1") == p("<bg #00A000><fg #ff0000>1") == "\x1b[48;2;0;160;0m"
        "\x1b[38;2;255;0;0m"
        "1"
    )

    assert p("<fg>1</fg>") == "<fg>1</fg>"
    assert p("<fg >1</fg >") == "<fg >1</fg >"
    assert p("<fg ,>1</fg ,>") == "<fg ,>1</fg ,>"
    assert p("<fg ,,>1</fg ,,>") == "<fg ,,>1</fg ,,>"
    assert p("<fg ,,,>1</fg ,,,>") == "<fg ,,,>1</fg ,,,>"
    assert p("<fg 1,2,>1</fg 1,2,>") == "<fg 1,2,>1</fg 1,2,>"
    assert p("<fg 256,120,120>1</fg 256,120,120>") == "<fg 256,120,120>1</fg 256,120,120>"


def test_nested():
    assert (
        p("0<b>1<d>2</d>3</b>4")
        == "0" + S.BRIGHT + "1" + S.DIM + "2" + S.RESET_ALL + S.BRIGHT + "3" + S.RESET_ALL + "4"
    )
    assert (
        p("<d>0<b>1<d>2</d>3</b>4</d>")
        == S.DIM
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
        + S.RESET_ALL
    )


def test_mismatched_error():
    with pytest.raises(ValueError):
        p("<b>1</d>")

    with pytest.raises(ValueError):
        p("</b>")

    with pytest.raises(ValueError):
        p("<b>1</b></b>")

    with pytest.raises(ValueError):
        p("<red><b>1</b></b></red>")

    with pytest.raises(ValueError):
        p("<tag>1</b>")


def test_unbalanced_error():
    with pytest.raises(ValueError):
        p("<r><Y>1</r>2</Y>")

    with pytest.raises(ValueError):
        p("<r><r><Y>1</r>2</Y></r>")

    with pytest.raises(ValueError):
        p("<r><Y><r></r></r></Y>")


def test_strict_parsing():
    with pytest.raises(ValueError):
        p("<b>", strict=True)

    with pytest.raises(ValueError):
        p("<Y><b></b>", strict=True)

    with pytest.raises(ValueError):
        p("<b><b></b>", strict=True)


def test_permissive_parsing():
    assert p("<b>", strict=False) == S.BRIGHT
    assert p("<Y><b></b>", strict=False) == B.YELLOW + p("<b></b>") + B.YELLOW
    assert p("<b><b></b>", strict=False) == S.BRIGHT + p("<b></b>") + S.BRIGHT


def test_unknown_tags():
    assert p("<tag>1</tag>") == "<tag>1</tag>"
    assert p("<tag>") == "<tag>"
    assert p("</tag>") == "</tag>"

    assert p("<b>1</b><tag>2</tag>") == S.BRIGHT + "1" + S.RESET_ALL + "<tag>2</tag>"
    assert p("<tag>1</tag><b>2</b>") == "<tag>1</tag>" + S.BRIGHT + "2" + S.RESET_ALL

    assert (
        p("<b>1</b><tag>2</tag><b>3</b>")
        == S.BRIGHT + "1" + S.RESET_ALL + "<tag>2</tag>" + S.BRIGHT + "3" + S.RESET_ALL
    )
    assert (
        p("<tag>1</tag><b>2</b><tag>3</tag>")
        == "<tag>1</tag>" + S.BRIGHT + "2" + S.RESET_ALL + "<tag>3</tag>"
    )

    assert p("<b><tag>1</tag></b>") == S.BRIGHT + "<tag>1</tag>" + S.RESET_ALL
    assert p("<tag><b>1</b></tag>") == "<tag>" + S.BRIGHT + "1" + S.RESET_ALL + "</tag>"

    assert p("<b><tag>1</tag>") == S.BRIGHT + "<tag>1</tag>"
    assert p("<tag>1</tag><b>") == "<tag>1</tag>" + S.BRIGHT

    assert p("<b><tag>") == S.BRIGHT + "<tag>"
    assert p("<tag><b>") == "<tag>" + S.BRIGHT

    assert p("<b></tag>") == S.BRIGHT + "</tag>"
    assert p("</tag><b>") == "</tag>" + S.BRIGHT


def test_strip():
    assert s("<b>1</b>2<d>3</d>") == "123"
    assert s("<bold,red,yellow>1</bold,red,yellow>") == "1"
    assert s("<r><tag>1</tag></r>") == "<tag>1</tag>"
    assert s("<tag><r>1</r></tag>") == "<tag>1</tag>"
    assert s("<tag><r>1</tag></r>") == "<tag>1</tag>"

    markups = {"red": "", "b,g,r": "", "fg 1,2,3": ""}
    am = AnsiMarkup(custom_markups=markups, strip=True)
    assert am.feed("<red>1</red><b,g,r>2</b,g,r><fg 1,2,3>3</fg 1,2,3>", strict=True) == "123"


def test_invalid_strip():
    with pytest.raises(ValueError):
        s("<r><b>1</r></b>", strict=True)

    with pytest.raises(ValueError):
        s("<fg red>1<fg red>", strict=True)


def test_usertags():
    user_markups = {"info": F.GREEN + S.BRIGHT, "info1": p("<g><b>", strict=False)}

    am = AnsiMarkup(custom_markups=user_markups, strip=False)
    assert am.feed("<info>1</info>", strict=True) == F.GREEN + S.BRIGHT + "1" + S.RESET_ALL
    assert am.feed("<info>1</info>", strict=True) == am.feed("<info1>1</info1>", strict=True)
    am = AnsiMarkup(custom_markups=user_markups, strip=True)
    assert am.feed("<info1>1</info1>", strict=True) == "1"


def test_tag_chars_conflicting():
    assert p("<r>2 > 1</r>") == F.RED + "2 > 1" + S.RESET_ALL
    assert p("<r>1 < 2</r>") == F.RED + "1 < 2" + S.RESET_ALL
    assert p("<r>1 </ 2</r>") == F.RED + "1 </ 2" + S.RESET_ALL
    assert s("<r>2 > 1</r>") == "2 > 1"
    assert s("<r>1 < 2</r>") == "1 < 2"
    assert s("<r>1 </ 2</r>") == "1 </ 2"

    assert p("{: <10}<r>1</r>") == "{: <10}" + F.RED + "1" + S.RESET_ALL
    assert p("{: </10}<r>1</r>") == "{: </10}" + F.RED + "1" + S.RESET_ALL
    assert s("{: <10}<r>1</r>") == "{: <10}1"
    assert s("{: </10}<r>1</r>") == "{: </10}1"

    assert p("<r>1</r>{: >10}") == F.RED + "1" + S.RESET_ALL + "{: >10}"
    assert s("<r>1</r>{: >10}") == "1{: >10}"

    assert p("<1<r>2</r>3>") == "<1" + F.RED + "2" + S.RESET_ALL + "3>"
    assert p("</1<r>2</r>3>") == "</1" + F.RED + "2" + S.RESET_ALL + "3>"
    assert p("<1<r>2 < 3</r>4>") == "<1" + F.RED + "2 < 3" + S.RESET_ALL + "4>"
    assert p("<1<r>2 </ 3</r>4>") == "<1" + F.RED + "2 </ 3" + S.RESET_ALL + "4>"
    assert p("<1<r>3 > 2</r>4>") == "<1" + F.RED + "3 > 2" + S.RESET_ALL + "4>"
    assert s("<1<r>2</r>3>") == "<123>"
    assert s("</1<r>2</r>3>") == "</123>"
    assert s("<1<r>2 < 3</r>4>") == "<12 < 34>"
    assert s("<1<r>2 </ 3</r>4>") == "<12 </ 34>"
    assert s("<1<r>3 > 2</r>4>") == "<13 > 24>"
