import re
from string import Formatter


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


class TokenType:
    TEXT = 1
    ANSI = 2
    LEVEL = 3
    CLOSING = 4


class AnsiParser:

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

    def __init__(self):
        self._tokens = []
        self._tags = []
        self._tokens_tags = []

    @staticmethod
    def colorize(tokens, ansi_level):
        output = ""

        for type_, value in tokens:
            if type_ == TokenType.LEVEL:
                if ansi_level is None:
                    raise ValueError(
                        "The '<level>' color tag is not allowed in this context, "
                        "it has not yet been associated to any color value."
                    )
                value = ansi_level
            output += value
        return output

    @staticmethod
    def strip(tokens):
        output = ""
        for type_, value in tokens:
            if type_ == TokenType.TEXT:
                output += value
        return output

    def feed(self, text, *, raw=False):
        if raw:
            self._tokens.append((TokenType.TEXT, text))
            return

        position = 0

        for match in self._regex_tag.finditer(text):
            markup, tag = match.group(0), match.group(1)

            self._tokens.append((TokenType.TEXT, text[position : match.start()]))

            position = match.end()

            if markup[0] == "\\":
                self._tokens.append((TokenType.TEXT, markup[1:]))
                continue

            if markup[1] == "/":
                if self._tags and (tag == "" or tag == self._tags[-1]):
                    self._tags.pop()
                    self._tokens_tags.pop()
                    self._tokens.append((TokenType.CLOSING, "\033[0m"))
                    self._tokens.extend(self._tokens_tags)
                    continue
                elif tag in self._tags:
                    raise ValueError('Closing tag "%s" violates nesting rules' % markup)
                else:
                    raise ValueError('Closing tag "%s" has no corresponding opening tag' % markup)

            if tag in {"lvl", "level"}:
                token = (TokenType.LEVEL, None)
            else:
                ansi = self._get_ansicode(tag)

                if ansi is None:
                    raise ValueError(
                        'Tag "%s" does not corespond to any known ansi directive, '
                        "make sure you did not misspelled it (or prepend '\\' to escape it)"
                        % markup
                    )

                token = (TokenType.ANSI, ansi)

            self._tags.append(tag)
            self._tokens_tags.append(token)
            self._tokens.append(token)

        self._tokens.append((TokenType.TEXT, text[position:]))

    def wrap(self, tokens, ansi_level):
        wrapped = []
        for token in tokens:
            type_, _ = token
            wrapped.append(token)
            if type_ == TokenType.CLOSING:
                wrapped.extend(self._tokens_tags)

        return AnsiParser.colorize(wrapped, ansi_level)

    def done(self, *, strict=True):
        if strict and self._tags:
            faulty_tag = self._tags.pop(0)
            raise ValueError('Opening tag "<%s>" has no corresponding closing tag' % faulty_tag)
        return self._tokens

    def _get_ansicode(self, tag):
        style = self._style
        foreground = self._foreground
        background = self._background

        # Substitute on a direct match.
        if tag in style:
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


class ColoredString:
    def __init__(self, string, tokens):
        self.string = string
        self.tokens = tokens

    def colorize(self, ansi_level):
        return AnsiParser.colorize(self.tokens, ansi_level)

    def strip(self):
        return AnsiParser.strip(self.tokens)

    @classmethod
    def prepare_format(cls, string):
        tokens = ColoredString._parse_without_formatting(string)
        return cls(string, tokens)

    @classmethod
    def prepare_message(cls, string, args=(), kwargs={}):
        tokens = ColoredString._parse_with_formatting(string, args, kwargs)
        return cls(string, tokens)

    @classmethod
    def prepare_simple_message(cls, string):
        parser = AnsiParser()
        parser.feed(string)
        tokens = parser.done()
        return cls(string, tokens)

    @staticmethod
    def ansify(text):
        parser = AnsiParser()
        parser.feed(text.strip())
        tokens = parser.done(strict=False)
        return AnsiParser.colorize(tokens, None)

    @staticmethod
    def format_with_colored_message(string, kwargs, *, ansi_level, colored_message):
        tokens = ColoredString._parse_with_formatting(
            string, (), kwargs, ansi_level=ansi_level, colored_message=colored_message
        )
        return AnsiParser.colorize(tokens, ansi_level)

    @staticmethod
    def _parse_with_formatting(
        string,
        args,
        kwargs,
        *,
        recursion_depth=2,
        auto_arg_index=0,
        recursive=False,
        ansi_level=None,
        colored_message=None
    ):
        # This function re-implement Formatter._vformat()

        if recursion_depth < 0:
            raise ValueError("Max string recursion exceeded")

        formatter = Formatter()
        parser = AnsiParser()

        for literal_text, field_name, format_spec, conversion in formatter.parse(string):
            parser.feed(literal_text, raw=recursive)

            if field_name is not None:
                if field_name == "":
                    if auto_arg_index is False:
                        raise ValueError(
                            "cannot switch from manual field "
                            "specification to automatic field "
                            "numbering"
                        )
                    field_name = str(auto_arg_index)
                    auto_arg_index += 1
                elif field_name.isdigit():
                    if auto_arg_index:
                        raise ValueError(
                            "cannot switch from manual field "
                            "specification to automatic field "
                            "numbering"
                        )
                    auto_arg_index = False

                obj, _ = formatter.get_field(field_name, args, kwargs)

                # Will not match "message.attr" / "message[0]": in this case, the record["message"]
                # which contains the striped message will be used and no coloration is needed
                if field_name == "message" and not recursive and colored_message:
                    obj = parser.wrap(colored_message.tokens, ansi_level)

                obj = formatter.convert_field(obj, conversion)

                format_spec, auto_arg_index = ColoredString._parse_with_formatting(
                    format_spec,
                    args,
                    kwargs,
                    recursion_depth=recursion_depth - 1,
                    auto_arg_index=auto_arg_index,
                    recursive=True,
                )

                formatted = formatter.format_field(obj, format_spec)
                parser.feed(formatted, raw=True)

        tokens = parser.done()

        if recursive:
            return AnsiParser.strip(tokens), auto_arg_index

        return tokens

    @staticmethod
    def _parse_without_formatting(string):
        formatter = Formatter()
        parser = AnsiParser()

        for literal_text, field_name, format_spec, conversion in formatter.parse(string):
            if literal_text and literal_text[-1] in "{}":
                literal_text += literal_text[-1]

            parser.feed(literal_text)

            if field_name is not None:
                field = "{%s" % field_name
                if conversion:
                    field += "!%s" % conversion
                if format_spec:
                    field += ":%s" % format_spec
                field += "}"
                parser.feed(field, raw=True)

        return parser.done()
