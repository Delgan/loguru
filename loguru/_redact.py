"""Helper to scrub common secret patterns from log record messages.

Public API: :func:`redact`. Returns a Loguru patcher
(``Callable[[Record], None]``) suitable for :meth:`Logger.patch`. The
patcher rewrites ``record["message"]`` in place, replacing any built-in
or caller-supplied secret patterns with ``"[REDACTED]"``.

Built-in coverage:

* HTTP ``Authorization`` headers and bare ``Bearer``/``Token``/``Basic``
  schemes -- the scheme keyword is preserved, the credential is replaced.
* ``key=value`` and JSON-style ``"key": "value"`` pairs for common
  secret-bearing key names (``password``, ``token``, ``secret``,
  ``api_key``, ``apikey``).
* Provider-specific opaque tokens -- whole match replaced:
  ``sk-`` prefixed alphanumeric, ``AKIA`` + 16 uppercase base32 chars
  (AWS access key IDs), ``ghp_`` prefixed alphanumeric (GitHub PATs).

The module targets Python >= 3.5 -- ``re.Pattern`` only became part of
``re``'s public API in Python 3.7, so the runtime ``isinstance`` check
resolves the compiled-pattern class via ``type(re.compile(""))``. The
type stub in ``loguru/__init__.pyi`` advertises ``typing.Pattern[str]``.
Inline scoped-flag syntax ``(?i:...)`` is also 3.7+, so the
case-insensitive patterns use the ``re.IGNORECASE`` flag instead.
"""

import re

_REDACTED = "[REDACTED]"

# ``re.Pattern`` only became part of ``re``'s public API in Python 3.7.
# loguru still supports 3.5/3.6, so we resolve the compiled-pattern class
# via ``type(re.compile(""))`` once at import.
_PATTERN_TYPE = type(re.compile(""))

# Secret-bearing key names (case-insensitive). ``api[_-]?key`` covers
# ``api_key``, ``apikey`` and ``api-key`` with one branch.
_SECRET_KEYS = r"password|token|secret|api[_-]?key"

# JSON-style ``"key": "value"`` form -- the key itself is quoted, so the
# unquoted ``key=value`` rule below would miss it. Both quote characters
# must match via back-reference so we don't span mismatched delimiters.
_JSON_KEY_VALUE_RE = re.compile(
    r"(?P<key_quote>[\"'])(?P<key>(?:" + _SECRET_KEYS + r"))(?P=key_quote)"
    r"(?P<sep>\s*:\s*)"
    r"(?P<value_quote>[\"'])(?P<value>(?:\\.|(?!(?P=value_quote)).)*)(?P=value_quote)",
    re.IGNORECASE,
)
_JSON_KEY_VALUE_SUB = (
    r"\g<key_quote>\g<key>\g<key_quote>\g<sep>\g<value_quote>" + _REDACTED + r"\g<value_quote>"
)

# Unquoted ``key=value`` / ``key: value``. The negative look-behind on
# ``[A-Za-z0-9_]`` prevents matching a key fragment inside a larger
# identifier (e.g. ``oauth=...`` would otherwise match ``auth=``).
_KEY_VALUE_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?P<key>(?:" + _SECRET_KEYS + r"))"
    r"(?P<sep>\s*[:=]\s*)"
    r"(?P<value>[^\s,&\"']+)",
    re.IGNORECASE,
)
_KEY_VALUE_SUB = r"\g<key>\g<sep>" + _REDACTED

# HTTP ``Authorization`` header values (Bearer / Token / Basic). Only
# the credential after the scheme is replaced.
_AUTH_HEADER_RE = re.compile(
    r"(?P<prefix>Authorization\s*:\s*(?:Bearer|Token|Basic)\s+)\S+",
    re.IGNORECASE,
)
_AUTH_HEADER_SUB = r"\g<prefix>" + _REDACTED

# Bare ``Bearer <token>`` / ``Token <token>`` / ``Basic <token>`` without
# a leading ``Authorization:`` header (e.g. inside curl examples or chat
# messages). ``re.IGNORECASE`` mirrors the header rule.
_BEARER_RE = re.compile(
    r"(?P<scheme>(?:Bearer|Token|Basic)\s+)(?P<token>[A-Za-z0-9+/=._\-]+)",
    re.IGNORECASE,
)
_BEARER_SUB = r"\g<scheme>" + _REDACTED

# Provider-specific opaque tokens -- whole match replaced. Look-arounds
# anchor on token-character boundaries so we don't redact a fragment of
# a longer alphanumeric blob.
_OPENAI_KEY_RE = re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9]{20,}(?![A-Za-z0-9])")
_AWS_KEY_RE = re.compile(r"(?<![A-Z0-9])AKIA[A-Z0-9]{16}(?![A-Z0-9])")
_GITHUB_PAT_RE = re.compile(r"(?<![A-Za-z0-9])ghp_[A-Za-z0-9]{36}(?![A-Za-z0-9])")

# Built-in patterns are compiled once at import time, so the patcher
# returned by :func:`redact` does no compilation per log record. Order
# matters: the ``Authorization`` header rule and JSON key=value rule run
# before the generic ``key=value`` and bare bearer-token fallback so
# they get first claim on overlapping text.
_BUILTIN_PATTERNS = (
    (_AUTH_HEADER_RE, _AUTH_HEADER_SUB),
    (_JSON_KEY_VALUE_RE, _JSON_KEY_VALUE_SUB),
    (_KEY_VALUE_RE, _KEY_VALUE_SUB),
    (_OPENAI_KEY_RE, _REDACTED),
    (_AWS_KEY_RE, _REDACTED),
    (_GITHUB_PAT_RE, _REDACTED),
    (_BEARER_RE, _BEARER_SUB),
)


def redact(*extra_patterns):
    """Return a Loguru patcher that scrubs common secrets from log messages.

    The returned callable is suitable for :meth:`Logger.patch`. Each log
    record's ``message`` is scanned for built-in secret patterns plus any
    additional patterns supplied via ``extra_patterns``; matches are
    replaced in place with ``"[REDACTED]"``.

    Built-in coverage: HTTP ``Authorization`` headers and bare
    ``Bearer``/``Token``/``Basic`` schemes (scheme preserved, value
    replaced); ``key=value`` and JSON ``"key": "value"`` forms for
    common secret keys (``password``, ``token``, ``secret``, ``api_key``,
    ``apikey``); ``sk-`` prefixed alphanumeric strings, AWS access key
    IDs (``AKIA`` + 16 chars), and GitHub PATs (``ghp_`` + 36 chars).

    Each item in ``extra_patterns`` may be a regex string or a
    pre-compiled regex pattern object. Strings are compiled (with
    :data:`re.IGNORECASE`) when :func:`redact` is called -- so an
    invalid regex raises :class:`re.error` eagerly at call time -- and
    the returned patcher performs no compilation per log record. Each
    call to :func:`redact` returns an independent patcher.

    Raises :class:`TypeError` if an ``extra_patterns`` element is
    neither a string nor a compiled regex pattern object.
    """
    compiled_extras = []
    for pattern in extra_patterns:
        if isinstance(pattern, str):
            # ``re.compile`` raises ``re.error`` at call time for invalid
            # regex. ``re.IGNORECASE`` matches the documented public
            # behavior; pre-compiled regex objects are passed through
            # untouched so callers stay in control of their own flags.
            compiled_extras.append(re.compile(pattern, re.IGNORECASE))
        elif isinstance(pattern, _PATTERN_TYPE):
            compiled_extras.append(pattern)
        else:
            raise TypeError(
                "redact() extra patterns must be str or compiled regex, got %r"
                % type(pattern).__name__
            )
    extras = tuple(compiled_extras)

    def patcher(record):
        message = record["message"]
        for pattern, replacement in _BUILTIN_PATTERNS:
            message = pattern.sub(replacement, message)
        for pattern in extras:
            message = pattern.sub(_REDACTED, message)
        record["message"] = message

    return patcher
