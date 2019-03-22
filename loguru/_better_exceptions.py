import builtins
import distutils.sysconfig
import inspect
import io
import keyword
import linecache
import os
import re
import site
import sys
import sysconfig
import tokenize
import traceback
from collections import namedtuple


loguru_traceback = namedtuple("loguru_traceback", ("tb_frame", "tb_lasti", "tb_lineno", "tb_next"))


loguru_frame = namedtuple(
    "loguru_frame",
    ("f_back", "f_builtins", "f_code", "f_globals", "f_lasti", "f_lineno", "f_locals", "f_trace"),
)


loguru_code = namedtuple(
    "loguru_code",
    (
        "co_argcount",
        "co_code",
        "co_cellvars",
        "co_consts",
        "co_filename",
        "co_firstlineno",
        "co_flags",
        "co_lnotab",
        "co_freevars",
        "co_kwonlyargcount",
        "co_name",
        "co_names",
        "co_nlocals",
        "co_stacksize",
        "co_varnames",
    ),
)


class SyntaxHighlighter:

    default_style = {
        "comment": "\x1b[30m\x1b[1m{}\x1b[0m",
        "keyword": "\x1b[35m\x1b[1m{}\x1b[0m",
        "builtin": "\x1b[1m{}\x1b[0m",
        "string": "\x1b[36m{}\x1b[0m",
        "number": "\x1b[34m\x1b[1m{}\x1b[0m",
        "operator": "\x1b[35m\x1b[1m{}\x1b[0m",
        "punctuation": "\x1b[1m{}\x1b[0m",
        "constant": "\x1b[36m\x1b[1m{}\x1b[0m",
        "identifier": "\x1b[1m{}\x1b[0m",
        "other": "{}",
    }

    builtins = set(dir(builtins))
    constants = {"True", "False", "None"}
    punctation = {"(", ")", "[", "]", "{", "}", ":", ",", ";"}

    def __init__(self, style=None):
        self._style = style or self.default_style

    def highlight(self, source):
        style = self._style
        row, column = 0, 0
        output = ""

        for token in self.tokenize(source):
            type_, string, start, end, line = token

            if type_ == tokenize.NAME:
                if string in self.constants:
                    color = style["constant"]
                elif keyword.iskeyword(string):
                    color = style["keyword"]
                elif string in self.builtins:
                    color = style["builtin"]
                else:
                    color = style["identifier"]
            elif type_ == tokenize.OP:
                if string in self.punctation:
                    color = style["punctuation"]
                else:
                    color = style["operator"]
            elif type_ == tokenize.NUMBER:
                color = style["number"]
            elif type_ == tokenize.STRING:
                color = style["string"]
            elif type_ == tokenize.COMMENT:
                color = style["comment"]
            else:
                color = style["other"]

            start_row, start_column = start
            _, end_column = end

            if start_row != row:
                source = source[:column]
                row, column = start_row, 0

            if type_ != tokenize.ENCODING:
                output += line[column:start_column]
                output += color.format(string)

            column = end_column

        output += source[column:]

        return output

    @staticmethod
    def tokenize(source):
        # Worth reading: https://www.asmeurer.com/brown-water-python/
        source = source.encode("utf-8")
        source = io.BytesIO(source)

        try:
            yield from tokenize.tokenize(source.readline)
        except tokenize.TokenError:
            return


class ExceptionExtender:

    _catch_point_identifier = " <Loguru catch point here>"

    def extend_traceback(self, tb, *, decorated=False):
        if tb is None:
            return None

        frame = tb.tb_frame

        if decorated:
            bad_frame = (tb.tb_frame.f_code.co_filename, tb.tb_frame.f_lineno)
            tb = tb.tb_next
            caught = False
        else:
            bad_frame = None
            tb = self._make_catch_traceback(tb.tb_frame, tb.tb_lasti, tb.tb_lineno, tb.tb_next)
            caught = True

        while True:
            frame = frame.f_back

            if not frame:
                break

            if (frame.f_code.co_filename, frame.f_lineno) == bad_frame:
                continue

            if not caught:
                caught = True
                tb = self._make_catch_traceback(frame, frame.f_lasti, frame.f_lineno, tb)
            else:
                tb = loguru_traceback(frame, frame.f_lasti, frame.f_lineno, tb)

        return tb

    def reformat(self, error):
        regex = r".*%s.*" % re.escape(self._catch_point_identifier)

        def replace(match):
            return match.group(0).replace(" ", ">", 1).replace(self._catch_point_identifier, "")

        return re.sub(regex, replace, error, re.MULTILINE)

    def _make_catch_traceback(self, frame, lasti, lineno, next_):
        f = frame
        c = frame.f_code
        code = loguru_code(
            c.co_argcount,
            c.co_code,
            c.co_cellvars,
            c.co_consts,
            c.co_filename,
            c.co_firstlineno,
            c.co_flags,
            c.co_lnotab,
            c.co_freevars,
            c.co_kwonlyargcount,
            c.co_name + self._catch_point_identifier,
            c.co_names,
            c.co_nlocals,
            c.co_stacksize,
            c.co_varnames,
        )
        frame = loguru_frame(
            f.f_back, f.f_builtins, code, f.f_globals, f.f_lasti, f.f_lineno, f.f_locals, f.f_trace
        )
        tb = loguru_traceback(frame, lasti, lineno, next_)
        return tb


class ExceptionFormatter:

    default_theme = {
        # Some terminals support "31+1" (red + bold) but not "91" (bright red), see Repl.it
        "introduction": "\x1b[33m\x1b[1m{}\x1b[0m",
        "cause": "\x1b[1m{}\x1b[0m",
        "context": "\x1b[1m{}\x1b[0m",
        "dirname": "\x1b[32m{}\x1b[0m",
        "basename": "\x1b[32m\x1b[1m{}\x1b[0m",
        "line": "\x1b[33m{}\x1b[0m",
        "function": "\x1b[35m{}\x1b[0m",
        "exception_type": "\x1b[31m\x1b[1m{}\x1b[0m",
        "exception_value": "\x1b[1m{}\x1b[0m",
        "arrows": "\x1b[36m{}\x1b[0m",
        "value": "\x1b[36m\x1b[1m{}\x1b[0m",
    }

    def __init__(
        self,
        colorize=False,
        show_values=True,
        theme=None,
        style=None,
        max_length=128,
        encoding="ascii",
    ):
        self._colorize = colorize
        self._show_values = show_values
        self._theme = theme or self.default_theme
        self._syntax_highlighter = SyntaxHighlighter(style)
        self._max_length = max_length
        self._encoding = encoding
        self._lib_dirs = self._get_lib_dirs()
        self._pipe_char = self._get_char("\u2502", "|")
        self._cap_char = self._get_char("\u2514", "->")
        self._location_regex = (
            r'  File "(?P<file>.*?)", line (?P<line>[^,]+)(?:, in (?P<function>.*))?'
            r"(?P<end>\n[\s\S]*)"
        )

    def _get_char(self, char, default):
        try:
            char.encode(self._encoding)
        except UnicodeEncodeError:
            return default
        else:
            return char

    def _get_lib_dirs(self):
        # https://git.io/fh5wm
        # https://stackoverflow.com/q/122327/2291710
        lib_dirs = [
            sysconfig.get_path("stdlib"),
            site.USER_SITE,
            distutils.sysconfig.get_python_lib(),
        ]

        try:
            real_prefix = sys.real_prefix
        except AttributeError:
            pass
        else:
            lib_dirs.append(sys.prefix)
            lib_dirs.append(sysconfig.get_path("stdlib").replace(sys.prefix, real_prefix))

        try:
            lib_dirs += site.getsitepackages()
        except AttributeError:
            pass

        return [os.path.abspath(d) + os.sep for d in lib_dirs]

    def _colorize_location(self, file, line, function, end):
        dirname, basename = os.path.split(file)

        if dirname:
            dirname += os.sep

        dirname = self._theme["dirname"].format(dirname)
        basename = self._theme["basename"].format(basename)
        file = dirname + basename

        line = self._theme["line"].format(line)

        if function is not None:
            function = self._theme["function"].format(function)
            frame = '  File "{}", line {}, in {}{}'.format(file, line, function, end)
        else:
            frame = '  File "{}, line {}{}'.format(file, line, end)

        return frame

    def _format_value(self, v):
        try:
            v = repr(v)
        except Exception:
            v = "<unprintable %s object>" % type(v).__name__

        max_length = self._max_length
        if max_length is not None and len(v) > max_length:
            v = v[:max_length] + "..."
        return v

    def _is_file_mine(self, file):
        filepath = os.path.abspath(file).lower()
        if not filepath.endswith(".py"):
            return False
        return not any(filepath.startswith(d.lower()) for d in self._lib_dirs)

    def _extract_frames(self, tb):
        frames = []

        while tb:
            frames.append(tb)
            tb = tb.tb_next

        return frames

    def _get_frame_information(self, frame):
        lineno = frame.tb_lineno
        filename = frame.tb_frame.f_code.co_filename
        function = frame.tb_frame.f_code.co_name
        source = linecache.getline(filename, lineno).strip()
        if self._show_values:
            relevant_values = self._get_relevant_values(source, frame.tb_frame)
        else:
            relevant_values = None
        return filename, lineno, function, source, relevant_values

    def _get_relevant_values(self, source, frame):
        values = []
        value = None
        is_attribute = False
        is_valid_value = False

        for token in self._syntax_highlighter.tokenize(source):
            type_, string, (_, col), *_ = token

            if type_ == tokenize.NAME and not keyword.iskeyword(string):
                if not is_attribute:
                    for variables in (frame.f_locals, frame.f_globals):
                        try:
                            value = variables[string]
                        except KeyError:
                            continue
                        else:
                            is_valid_value = True
                            values.append((col, self._format_value(value)))
                            break
                elif is_valid_value:
                    try:
                        value = inspect.getattr_static(value, string)
                    except AttributeError:
                        is_valid_value = False
                    else:
                        values.append((col, self._format_value(value)))
            elif type_ == tokenize.OP and string == ".":
                is_attribute = True
            else:
                is_attribute = False
                is_valid_value = False

        values.sort()

        return values

    def _format_relevant_values(self, relevant_values, colorize):
        lines = []

        for i in reversed(range(len(relevant_values))):
            col, value = relevant_values[i]
            pipe_cols = [pcol for pcol, _ in relevant_values[:i]]
            pre_line = ""
            index = 0

            for pc in pipe_cols:
                pre_line += (" " * (pc - index)) + self._pipe_char
                index = pc + 1

            pre_line += " " * (col - index)
            value_lines = value.split("\n")

            for n, value_line in enumerate(value_lines):
                if n == 0:
                    arrows = pre_line + self._cap_char + " "
                else:
                    arrows = pre_line + " " * (len(self._cap_char) + 1)

                if colorize:
                    arrows = self._theme["arrows"].format(arrows)
                    value_line = self._theme["value"].format(value_line)

                lines.append(arrows + value_line)

        return lines

    def _format_frames(self, frames):
        formatted_frames = []

        for frame in frames:
            filename, lineno, function, source, relevant_values = self._get_frame_information(frame)

            if source:
                is_mine = self._is_file_mine(filename)

                if self._colorize and is_mine:
                    source = self._syntax_highlighter.highlight(source)

                if self._show_values:
                    values = self._format_relevant_values(
                        relevant_values, self._colorize and is_mine
                    )
                    frame_lines = [source] + values
                    source = "\n    ".join(frame_lines)

            formatted_frames.append((filename, lineno, function, source))

        return formatted_frames

    def _format_locations(self, formatted_frames):
        lines = []
        prepend_with_new_line = False

        for frame in formatted_frames:
            match = re.match(self._location_regex, frame)

            if match:
                group = match.groupdict()
                file, line, function, end = (
                    group["file"],
                    group["line"],
                    group["function"],
                    group["end"],
                )

                is_mine = self._is_file_mine(file)

                if self._colorize and is_mine:
                    frame = self._colorize_location(file, line, function, end)
                if self._show_values and (is_mine or prepend_with_new_line):
                    frame = "\n" + frame

                prepend_with_new_line = is_mine

            lines.append(frame)

        return lines

    def _format_exception(self, value, tb, seen=None):
        # Implemented from built-in traceback module: https://git.io/fhHKw
        exc_type, exc_value, exc_traceback = type(value), value, tb

        if seen is None:
            seen = set()

        seen.add(id(exc_value))

        if exc_value:
            if exc_value.__cause__ is not None and id(exc_value.__cause__) not in seen:
                for text in self._format_exception(
                    exc_value.__cause__, exc_value.__cause__.__traceback__, seen=seen
                ):
                    yield text
                cause = "The above exception was the direct cause of the following exception:"
                if self._colorize:
                    cause = self._theme["cause"].format(cause)
                if self._show_values:
                    yield "\n\n" + cause + "\n\n\n"
                else:
                    yield "\n" + cause + "\n\n"

            elif (
                exc_value.__context__ is not None
                and id(exc_value.__context__) not in seen
                and not exc_value.__suppress_context__
            ):
                for text in self._format_exception(
                    exc_value.__context__, exc_value.__context__.__traceback__, seen=seen
                ):
                    yield text
                context = "During handling of the above exception, another exception occurred:"
                if self._colorize:
                    context = self._theme["context"].format(context)
                if self._show_values:
                    yield "\n\n" + context + "\n\n\n"
                else:
                    yield "\n" + context + "\n\n"

        if exc_traceback is not None:
            introduction = "Traceback (most recent call last):"
            if self._colorize:
                introduction = self._theme["introduction"].format(introduction)
            yield introduction + "\n"

        frames = self._extract_frames(exc_traceback)
        formatted_frames = self._format_frames(frames)

        if issubclass(exc_type, AssertionError) and not str(exc_value) and self._show_values:
            *_, final_source, _ = self._get_frame_information(frames[-1])
            if self._colorize:
                final_source = self._syntax_highlighter.highlight(final_source)
            exc_value.args = (final_source,)

        exception_only = traceback.format_exception_only(exc_type, exc_value)

        # This relies on implementation details: https://git.io/fjJTm
        if self._colorize and len(exception_only) >= 3 and issubclass(exc_type, SyntaxError):
            match = re.match(self._location_regex, exception_only[0])
            group = match.groupdict()
            exception_only[0] = '\n' + self._colorize_location(
                group["file"], group["line"], group["function"], group["end"]
            )
            exception_only[1] = self._syntax_highlighter.highlight(exception_only[1])

        error_message = exception_only[-1]

        if self._colorize:
            error_message = error_message[:-1]  # Avoid closing ansi tag after final newline
            if ":" in error_message:
                exception_type, exception_value = error_message.split(":", 1)
                exception_type = self._theme["exception_type"].format(exception_type)
                exception_value = self._theme["exception_value"].format(exception_value)
                error_message = exception_type + ":" + exception_value
            else:
                error_message = self._theme["exception_type"].format(error_message)
            error_message += "\n"

        if formatted_frames and self._show_values:
            error_message = "\n" + error_message

        exception_only[-1] = error_message

        frames_lines = traceback.format_list(formatted_frames) + exception_only
        lines = self._format_locations(frames_lines)

        yield "".join(lines)

    def format_exception(self, type_, value, tb):
        yield from self._format_exception(value, tb)
