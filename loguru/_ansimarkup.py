import re

from colorama.ansi import AnsiCodes
from colorama import Fore, Back, Style


class AnsiExtendedStyle(AnsiCodes):
    ITALIC = 3
    UNDERLINE = 4
    BLINK = 5
    REVERSE = 7
    STRIKE = 8
    HIDE = 9


ExtendedStyle = AnsiExtendedStyle()


class AnsiMarkup:

    _style = {
        "b": Style.BRIGHT,
        "d": Style.DIM,
        "n": Style.NORMAL,
        "0": Style.RESET_ALL,
        "h": ExtendedStyle.HIDE,
        "i": ExtendedStyle.ITALIC,
        "l": ExtendedStyle.BLINK,
        "s": ExtendedStyle.STRIKE,
        "u": ExtendedStyle.UNDERLINE,
        "v": ExtendedStyle.REVERSE,
        "bold": Style.BRIGHT,
        "dim": Style.DIM,
        "normal": Style.NORMAL,
        "reset": Style.RESET_ALL,
        "hide": ExtendedStyle.HIDE,
        "italic": ExtendedStyle.ITALIC,
        "blink": ExtendedStyle.BLINK,
        "strike": ExtendedStyle.STRIKE,
        "underline": ExtendedStyle.UNDERLINE,
        "reverse": ExtendedStyle.REVERSE,
    }

    _foreground = {
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

    _background = {
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

    def __init__(self, tags=None, strict=False):
        self.user_tags = tags or {}
        self.strict = strict
        self.re_tag = re.compile(r"</?([^<>]+)>")

    def parse(self, text):
        tags, results = [], []

        text = self.re_tag.sub(lambda m: self._sub_tag(m, tags, results), text)

        if self.strict and tags:
            raise ValueError('Opening tag "<%s>" has no corresponding closing tag' % tags.pop(0))

        return text

    def strip(self, text):
        tags, results = [], []
        return self.re_tag.sub(lambda m: self._clear_tag(m, tags, results), text)

    def get_ansicode(self, tag):
        # User-defined tags take preference over all other.
        if tag in self.user_tags:
            return self.user_tags[tag]

        # Substitute on a direct match.
        elif tag in self._style:
            return self._style[tag]
        elif tag in self._foreground:
            return self._foreground[tag]
        elif tag in self._background:
            return self._background[tag]

        # An alternative syntax for setting the color (e.g. <fg red>, <bg red>).
        elif tag.startswith("fg ") or tag.startswith("bg "):
            st, color = tag[:2], tag[3:]
            code = "38" if st == "fg" else "48"

            if st == "fg" and color in self._foreground:
                return self._foreground[color]
            elif st == "bg" and color.islower() and color.upper() in self._background:
                return self._background[color.upper()]
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

        # Shorthand formats (e.g. <red,blue>, <bold,red,blue>).
        elif "," in tag:
            el_count = tag.count(",")

            if el_count == 1:
                fg, bg = tag.split(",")
                if fg in self._foreground and bg.islower() and bg.upper() in self._background:
                    return self._foreground[fg] + self._background[bg.upper()]

            elif el_count == 2:
                st, fg, bg = tag.split(",")
                if st in self._style and (fg != "" or bg != ""):
                    if fg == "" or fg in self._foreground:
                        if bg == "" or (bg.islower() and bg.upper() in self._background):
                            st = self._style[st]
                            fg = self._foreground.get(fg, "")
                            bg = self._background.get(bg.upper(), "")
                            return st + fg + bg

        return None

    def _sub_tag(self, match, tag_list, res_list):
        markup, tag = match.group(0), match.group(1)
        closing = markup[1] == "/"

        # Early exit if the closing tag matches the last known opening tag.
        if closing and tag_list and tag_list[-1] == tag:
            tag_list.pop()
            res_list.pop()
            return Style.RESET_ALL + "".join(res_list)

        res = self.get_ansicode(tag)

        # If nothing matches, return the full tag (i.e. <unknown>text</...>).
        if res is None:
            return markup

        # If closing tag is known, but did not early exit, something is wrong.
        if closing:
            if tag in tag_list:
                raise ValueError('Closing tag "%s" violates nesting rules.' % markup)
            else:
                raise ValueError('Closing tag "%s" has no corresponding opening tag' % markup)

        tag_list.append(tag)
        res_list.append(res)

        return res

    def _clear_tag(self, match, tag_list, res_list):
        pre_length = len(tag_list)
        try:
            self._sub_tag(match, tag_list, res_list)

            # If list did not change, the tag is unknown
            if len(tag_list) == pre_length:
                return match.group(0)

            # Otherwise, tag matched so remove it
            else:
                return ""

        # Tag matched but is invalid, remove it anyway
        except ValueError:
            return ""
