"""Regression test for {time:x} negative timestamp truncation bug (loguru #1501).

The ``x`` token computes epoch microseconds as
``int(dt.timestamp()) * 1000000 + dt.microsecond``.  For negative timestamps
with a fractional part, ``int()`` truncates toward zero instead of flooring,
producing an incorrect result.
"""
from datetime import timezone

from loguru._datetime import _compile_format


def _format(dt, spec="x"):
    """Format a single datetime using a Loguru time-spec token."""
    formatter = _compile_format(spec)
    # The returned partial is _loguru_datetime_formatter(is_utc, fmt, formatters).
    # We can call it with (t, dt) where t is a time.struct_time.
    import time as _time

    t = _time.struct_time(dt.timetuple())
    # _loguru_datetime_formatter(is_utc, format_string, formatters)(value, dt)
    # Actually it's a partial; let's check its signature by calling directly.
    return formatter(t, dt)


def test_time_x_negative_timestamp():
    """Pre-epoch timestamp with fractional part should floor, not truncate."""
    dt = __import__("datetime").datetime(
        1969, 12, 31, 23, 59, 59, 500000, tzinfo=timezone.utc
    )
    result = _format(dt, "x")
    assert result == "-500000", f"expected '-500000', got {result!r}"


def test_time_x_positive_timestamp_still_correct():
    """Positive timestamp with fractional part should remain correct."""
    dt = __import__("datetime").datetime(
        2023, 1, 1, 0, 0, 0, 500, tzinfo=timezone.utc
    )
    result = _format(dt, "x")
    assert result == "1672531200000500", f"expected '1672531200000500', got {result!r}"