import typing as t

from mypy.nodes import StrExpr
from mypy.plugin import MethodContext, Plugin
from mypy.types import Type


def _loguru_logger_call_handler(ctx: MethodContext,) -> Type:
    msg_arg = ctx.args[0][0]
    assert isinstance(msg_arg, StrExpr)

    msg_value: str = msg_arg.value
    interpolation_args = []
    interpolation_kwargs = []

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
