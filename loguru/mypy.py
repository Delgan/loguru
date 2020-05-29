import string
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
    log_msg_expr = ctx.args[0][0]
    assert isinstance(log_msg_expr, StrExpr)

    # collect call args/kwargs
    call_args_count = len(ctx.args[1])
    call_kwargs = {kwarg_name: ctx.args[2][idx] for idx,kwarg_name in enumerate(ctx.arg_names[2])}

    # collect args/kwargs from string interpolation
    log_msg_value: str = log_msg_expr.value
    log_msg_expected_args_count = 0
    log_msg_expected_kwargs = []
    for res in string.Formatter().parse(log_msg_value):
        if res[1] is None:
            continue
        elif not res[1].strip():
            log_msg_expected_args_count += 1
        else:
            log_msg_expected_kwargs.append(res[1].strip())

    if log_msg_expected_args_count > call_args_count:
        ctx.api.msg.fail(
            f"Missing {log_msg_expected_args_count - call_args_count} positional arguments for log message",
            context=log_msg_expr,
            code=ERROR_BAD_ARG,
        )
        return ctx.default_return_type
    elif log_msg_expected_args_count < call_args_count:
        ctx.api.msg.warn(
            f"Expected {log_msg_expected_args_count}, but found {call_args_count} positional arguments for log message",
            context=log_msg_expr,
            code=ERROR_BAD_ARG,
        )
        return ctx.default_return_type

    for log_msg_kwarg in log_msg_expected_kwargs:
        maybe_kwarg_expr = call_kwargs.pop(log_msg_kwarg, None)
        if maybe_kwarg_expr is None:
            ctx.api.msg.fail(
                f"{log_msg_kwarg} keyword argument is missing", context=log_msg_expr, code=ERROR_BAD_KWARG,
            )
            return ctx.default_return_type
        # TODO add kwarg type being lambda or any other callable

    if call_kwargs:
        ctx.api.msg.fail(
            f"{call_kwargs.keys()} keyword argument are not present in log message", context=log_msg_expr, code=ERROR_BAD_KWARG,
        )

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
