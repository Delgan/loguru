import re


class Style:
    RESET_ALL = 0
    BOLD = 1
    DIM = 2
    ITALIC = 3
    UNDERLINE = 4
    BLINK = 5
    REVERSE = 7
    STRIKE = 8
    HIDE = 9
    NORMAL = 22


class Fore:
    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37
    RESET = 39

    LIGHTBLACK_EX = 90
    LIGHTRED_EX = 91
    LIGHTGREEN_EX = 92
    LIGHTYELLOW_EX = 93
    LIGHTBLUE_EX = 94
    LIGHTMAGENTA_EX = 95
    LIGHTCYAN_EX = 96
    LIGHTWHITE_EX = 97


class Back:
    BLACK = 40
    RED = 41
    GREEN = 42
    YELLOW = 43
    BLUE = 44
    MAGENTA = 45
    CYAN = 46
    WHITE = 47
    RESET = 49

    LIGHTBLACK_EX = 100
    LIGHTRED_EX = 101
    LIGHTGREEN_EX = 102
    LIGHTYELLOW_EX = 103
    LIGHTBLUE_EX = 104
    LIGHTMAGENTA_EX = 105
    LIGHTCYAN_EX = 106
    LIGHTWHITE_EX = 107


def ansi_escape(codes):
    return {name: "\033[%dm" % code for name, code in codes.items()}


class AnsiMarkup:

    _style = ansi_escape(
        {
            "b": Style.BOLD,
            "d": Style.DIM,
            "n": Style.NORMAL,
            "h": Style.HIDE,
            "i": Style.ITALIC,
            "l": Style.BLINK,
            "s": Style.STRIKE,
            "u": Style.UNDERLINE,
            "v": Style.REVERSE,
            "bold": Style.BOLD,
            "dim": Style.DIM,
            "normal": Style.NORMAL,
            "hide": Style.HIDE,
            "italic": Style.ITALIC,
            "blink": Style.BLINK,
            "strike": Style.STRIKE,
            "underline": Style.UNDERLINE,
            "reverse": Style.REVERSE,
        }
    )

    _foreground = ansi_escape(
        {
            "k": Fore.BLACK,
            "r": Fore.RED,
            "g": Fore.GREEN,
            "y": Fore.YELLOW,
            "e": Fore.BLUE,
            "m": Fore.MAGENTA,
            "c": Fore.CYAN,
            "w": Fore.WHITE,
            "lk": Fore.LIGHTBLACK_EX,
            "lr": Fore.LIGHTRED_EX,
            "lg": Fore.LIGHTGREEN_EX,
            "ly": Fore.LIGHTYELLOW_EX,
            "le": Fore.LIGHTBLUE_EX,
            "lm": Fore.LIGHTMAGENTA_EX,
            "lc": Fore.LIGHTCYAN_EX,
            "lw": Fore.LIGHTWHITE_EX,
            "black": Fore.BLACK,
            "red": Fore.RED,
            "green": Fore.GREEN,
            "yellow": Fore.YELLOW,
            "blue": Fore.BLUE,
            "magenta": Fore.MAGENTA,
            "cyan": Fore.CYAN,
            "white": Fore.WHITE,
            "light-black": Fore.LIGHTBLACK_EX,
            "light-red": Fore.LIGHTRED_EX,
            "light-green": Fore.LIGHTGREEN_EX,
            "light-yellow": Fore.LIGHTYELLOW_EX,
            "light-blue": Fore.LIGHTBLUE_EX,
            "light-magenta": Fore.LIGHTMAGENTA_EX,
            "light-cyan": Fore.LIGHTCYAN_EX,
            "light-white": Fore.LIGHTWHITE_EX,
        }
    )

    _background = ansi_escape(
        {
            "K": Back.BLACK,
            "R": Back.RED,
            "G": Back.GREEN,
            "Y": Back.YELLOW,
            "E": Back.BLUE,
            "M": Back.MAGENTA,
            "C": Back.CYAN,
            "W": Back.WHITE,
            "LK": Back.LIGHTBLACK_EX,
            "LR": Back.LIGHTRED_EX,
            "LG": Back.LIGHTGREEN_EX,
            "LY": Back.LIGHTYELLOW_EX,
            "LE": Back.LIGHTBLUE_EX,
            "LM": Back.LIGHTMAGENTA_EX,
            "LC": Back.LIGHTCYAN_EX,
            "LW": Back.LIGHTWHITE_EX,
            "BLACK": Back.BLACK,
            "RED": Back.RED,
            "GREEN": Back.GREEN,
            "YELLOW": Back.YELLOW,
            "BLUE": Back.BLUE,
            "MAGENTA": Back.MAGENTA,
            "CYAN": Back.CYAN,
            "WHITE": Back.WHITE,
            "LIGHT-BLACK": Back.LIGHTBLACK_EX,
            "LIGHT-RED": Back.LIGHTRED_EX,
            "LIGHT-GREEN": Back.LIGHTGREEN_EX,
            "LIGHT-YELLOW": Back.LIGHTYELLOW_EX,
            "LIGHT-BLUE": Back.LIGHTBLUE_EX,
            "LIGHT-MAGENTA": Back.LIGHTMAGENTA_EX,
            "LIGHT-CYAN": Back.LIGHTCYAN_EX,
            "LIGHT-WHITE": Back.LIGHTWHITE_EX,
        }
    )

    _regex_tag = re.compile(r"\\?</?((?:[fb]g\s)?[^<>\s]*)>")

    def __init__(self, custom_markups=None, strip=False):
        self._custom = custom_markups or {}
        self._strip = strip
        self._tags = []
        self._results = []

    def feed(self, text, *, strict=True):
        if strict:
            pre_tags = self._tags
            self._tags = []
        text = self._regex_tag.sub(self._sub_tag, text)
        if strict:
            if self._tags:
                faulty_tag = self._tags.pop(0)
                raise ValueError('Opening tag "<%s>" has no corresponding closing tag' % faulty_tag)
            self._tags = pre_tags
        return text

    def get_ansicode(self, tag):
        custom = self._custom
        style = self._style
        foreground = self._foreground
        background = self._background

        # User-defined tags take preference over all other.
        if tag in custom:
            return custom[tag]

        # Substitute on a direct match.
        elif tag in style:
            return style[tag]
        elif tag in foreground:
            return foreground[tag]
        elif tag in background:
            return background[tag]

        # An alternative syntax for setting the color (e.g. <fg red>, <bg red>).
        elif tag.startswith("fg ") or tag.startswith("bg "):
            st, color = tag[:2], tag[3:]
            code = "38" if st == "fg" else "48"

            if st == "fg" and color.lower() in foreground:
                return foreground[color.lower()]
            elif st == "bg" and color.upper() in background:
                return background[color.upper()]
            elif color.isdigit() and int(color) <= 255:
                return "\033[%s;5;%sm" % (code, color)
            elif re.match(r"#(?:[a-fA-F0-9]{3}){1,2}$", color):
                hex_color = color[1:]
                if len(hex_color) == 3:
                    hex_color *= 2
                rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
                return "\033[%s;2;%s;%s;%sm" % ((code,) + rgb)
            elif color.count(",") == 2:
                colors = tuple(color.split(","))
                if all(x.isdigit() and int(x) <= 255 for x in colors):
                    return "\033[%s;2;%s;%s;%sm" % ((code,) + colors)

        return None

    def _sub_tag(self, match):
        markup, tag = match.group(0), match.group(1)

        if markup[0] == "\\":
            return markup[1:]

        if markup[1] == "/":
            if self._tags and (tag == "" or tag == self._tags[-1]):
                self._tags.pop()
                self._results.pop()
                if self._strip:
                    return ""
                else:
                    return "\033[0m" + "".join(self._results)
            elif tag in self._tags:
                raise ValueError('Closing tag "%s" violates nesting rules' % markup)
            else:
                raise ValueError('Closing tag "%s" has no corresponding opening tag' % markup)

        res = self.get_ansicode(tag)

        if res is None:
            raise ValueError(
                'Tag "%s" does not corespond to any known ansi directive, '
                "make sure you did not misspelled it" % markup
            )

        self._tags.append(tag)
        self._results.append(res)

        if self._strip:
            return ""
        else:
            return res
