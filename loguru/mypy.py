import typing as t

from mypy.nodes import StrExpr
from mypy.plugin import MethodContext, Plugin
from mypy.errorcodes import ErrorCode
from mypy.types import Type


ERROR_BAD_ARG: t.Final[ErrorCode] = ErrorCode(
    "loguru-logger-arg",
    "Positional argument of loguru handler is not valid for given message",
    "loguru",
)
ERROR_BAD_KWARG: t.Final[ErrorCode] = ErrorCode(
    "loguru-logger-kwarg",
    "Named argument of loguru handler is not valid for given message",
    "loguru",
)


def _loguru_logger_call_handler(ctx: MethodContext,) -> Type:
    import string

    msg_arg = ctx.args[0][0]
    assert isinstance(msg_arg, StrExpr)

    msg_value: str = msg_arg.value
    msg_interpolation_args_count = 0
    msg_interpolation_kwargs = []

    for res in string.Formatter().parse(msg_value):
        if res[1] is None:
            # not a placeholder
            continue
        elif not res[1].strip():
            # positional placeholder
            msg_interpolation_args_count += 1
        else:
            msg_interpolation_kwargs.append(res[1].strip())

    total_f_string_args = len(msg_interpolation_kwargs) + msg_interpolation_args_count
    if total_f_string_args != len(ctx.args):
        if msg_interpolation_args_count:
            msg, code = (
                "No positional arguments found in message",
                ERROR_BAD_ARG,
            )
            ctx.api.msg.fail(
                msg, context=ctx, code=code,
            )
            return ctx.default_return_type
        if msg_interpolation_kwargs:
            msg, code = (
                "No named arguments found in message",
                ERROR_BAD_KWARG,
            )
            ctx.api.msg.fail(
                msg, context=ctx, code=code,
            )
            return ctx.default_return_type

    return ctx.default_return_type


class LoguruPlugin(Plugin):
    builtin_severities = (
        "info",
        "debug",
        "trace",
        "error",
        "exception",
    )

    def get_method_hook(
        self, fullname: str,
    ) -> t.Optional[t.Callable[[MethodContext], Type]]:
        if fullname.startswith("loguru"):
            _, maybe_severity = fullname.rsplit(".", 1)
            if maybe_severity in self.builtin_severities:
                return _loguru_logger_call_handler
        return super().get_method_hook(fullname)


def plugin(version: str) -> t.Type[LoguruPlugin]:
    return LoguruPlugin
