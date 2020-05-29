import string
import typing as t

from mypy.nodes import LambdaExpr, StrExpr, NameExpr, FuncItem
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


def _loguru_logger_call_handler(ctx: MethodContext) -> Type:
    log_msg_expr = ctx.args[0][0]
    assert isinstance(log_msg_expr, StrExpr)

    # collect call args/kwargs
    # due to funky structure mypy offers here, it's easier
    # to beg for forgiveness here
    try:
        call_args = ctx.args[1]
        call_args_count = len(call_args)
    except IndexError:
        call_args = []
        call_args_count = 0
    try:
        call_kwargs = {
            kwarg_name: ctx.args[2][idx]
            for idx, kwarg_name in enumerate(ctx.arg_names[2])
        }
    except IndexError:
        call_kwargs = {}

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
            f"Missing {log_msg_expected_args_count - call_args_count} "
            "positional arguments for log message",
            context=log_msg_expr,
            code=ERROR_BAD_ARG,
        )
        return ctx.default_return_type
    elif log_msg_expected_args_count < call_args_count:
        ctx.api.msg.note(
            f"Expected {log_msg_expected_args_count} but found {call_args_count} "
            "positional arguments for log message",
            context=log_msg_expr,
            code=ERROR_BAD_ARG,
        )
        return ctx.default_return_type
    else:
        for call_pos, call_arg in enumerate(call_args):
            if isinstance(call_arg, LambdaExpr) and call_arg.arguments:
                ctx.api.msg.fail(
                    f"Expected 0 arguments for <lambda>: {call_pos} arg ",
                    context=call_arg,
                    code=ERROR_BAD_ARG,
                )
            elif (
                isinstance(call_arg, NameExpr)
                and isinstance(call_arg.node, FuncItem)
                and call_arg.node.arguments
            ):
                ctx.api.msg.fail(
                    f"Expected 0 arguments for {call_arg.node.fullname}: {call_arg}",
                    context=call_arg,
                    code=ERROR_BAD_ARG,
                )

    for log_msg_kwarg in log_msg_expected_kwargs:
        maybe_kwarg_expr = call_kwargs.pop(log_msg_kwarg, None)
        if maybe_kwarg_expr is None:
            ctx.api.msg.fail(
                f"{log_msg_kwarg} keyword argument is missing",
                context=log_msg_expr,
                code=ERROR_BAD_KWARG,
            )
            return ctx.default_return_type
        elif isinstance(maybe_kwarg_expr, LambdaExpr) and maybe_kwarg_expr.arguments:
            ctx.api.msg.fail(
                f"Expected 0 arguments for <lambda>: {log_msg_kwarg} kwarg ",
                context=maybe_kwarg_expr,
                code=ERROR_BAD_KWARG,
            )
        elif (
            isinstance(maybe_kwarg_expr, NameExpr)
            and isinstance(maybe_kwarg_expr.node, FuncItem)
            and maybe_kwarg_expr.node.arguments
        ):
            ctx.api.msg.fail(
                f"Expected 0 arguments for {maybe_kwarg_expr.node.fullname}: {log_msg_kwarg}",
                context=maybe_kwarg_expr,
                code=ERROR_BAD_KWARG,
            )

    for extra_kwarg_name in call_kwargs:
        ctx.api.msg.fail(
            f"{extra_kwarg_name} keyword argument not found in log message",
            context=log_msg_expr,
            code=ERROR_BAD_KWARG,
        )

    return ctx.default_return_type


class LoguruPlugin(Plugin):
    builtin_severities = (
        "info",
        "debug",
        "warning",
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
