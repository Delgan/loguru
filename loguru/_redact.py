"""Helper to scrub common secret patterns from log record messages.

Public API: :func:`redact`. Returns a Loguru patcher
(``Callable[[Record], None]``) suitable for :meth:`Logger.patch`. The
patcher rewrites ``record["message"]`` in place, replacing any built-in
or caller-supplied secret patterns with ``"[REDACTED]"``.

Built-in coverage:

* URI userinfo (``scheme://user:pass@host`` -> ``scheme://[REDACTED]@host``)
* HTTP ``Authorization`` headers and bare ``Bearer``/``Token``/``Basic``
  schemes -- the scheme keyword is preserved, the credential is replaced.
* ``key=value`` / ``key: value`` for common secret-bearing key names
  (``password``, ``token``, ``secret``, ``api_key``, ``apikey``).
* AWS access key IDs (``AKIA`` + 16 base32 chars) -- whole match replaced.

Each call to :func:`redact` builds a *single* combined regex by joining
the built-in pattern sources with ``|`` and compiling once with
``re.IGNORECASE``. Caller-supplied patterns are appended to the same
combined regex, so the patcher does no per-record compilation. Caller
patterns may be regex source strings or pre-compiled regex objects;
strings are distinguished from compiled patterns via ``isinstance(x,
str)`` rather than ``isinstance(x, re.Pattern)`` (the latter is only
public from Python 3.7 onward and the runtime targets Python >= 3.5).

The runtime module deliberately carries no type annotations -- the
public type stub lives in :mod:`loguru.__init__.pyi` -- so this module
imports cleanly under every supported Python version.
"""

import re

_REDACTED = "[REDACTED]"

# Each entry: (top_level_group_name, regex_source, replacement_callable).
# The top-level named group lets the dispatch function identify which
# alternative matched (m.lastgroup is unreliable when an alternative
# contains nested named groups). Replacement callables receive the
# match object and return the redacted substring; they may interpolate
# preserved spans (key name, URI scheme, auth scheme) so only the
# secret value itself is replaced.
#
# Order matters: alternatives earlier in the list are tried first by
# the regex engine at each position. The Authorization header rule
# must precede the bare bearer-scheme rule so the header form gets
# first claim on overlapping text.
_BUILTIN_PATTERNS = [
    (
        "uri",
        # scheme://user:pass@host -- only the credentials span is
        # redacted; the scheme and the @host suffix are preserved.
        # The lookahead anchors on '@' so we only fire on URIs that
        # actually carry userinfo (ordinary http://host:port/path
        # never matches because it has no '@').
        r"(?P<uri>(?P<uri_scheme>[a-zA-Z][a-zA-Z0-9+.\-]*://)"
        r"[^@/\s:]+:[^@/\s]+(?=@))",
        lambda m: m.group("uri_scheme") + _REDACTED,
    ),
    (
        "auth",
        # Authorization: Bearer/Token/Basic <token> -- preserve the
        # header name, separator, and scheme keyword; redact the
        # credential.
        r"(?P<auth>(?P<auth_prefix>Authorization\s*:\s*"
        r"(?:Bearer|Token|Basic)\s+)\S+)",
        lambda m: m.group("auth_prefix") + _REDACTED,
    ),
    (
        "kv",
        # key=value / key: value with an unquoted value. The negative
        # look-behind on word characters prevents matching a key name
        # embedded inside a longer identifier (e.g. ``oauth=...``
        # would otherwise hit ``auth=...``). The value runs up to the
        # next whitespace, comma, ampersand, or quote so it does not
        # eat trailing log content.
        r"(?P<kv>(?<![A-Za-z0-9_])"
        r"(?P<kv_key>password|token|secret|api[_-]?key|apikey)"
        r"(?P<kv_sep>\s*[:=]\s*)"
        r"[^\s,&\"']+)",
        lambda m: m.group("kv_key") + m.group("kv_sep") + _REDACTED,
    ),
    (
        "bearer",
        # Bare ``Bearer <token>`` / ``Token <token>`` / ``Basic <token>``
        # without a leading ``Authorization:`` header (e.g. inside curl
        # examples). The look-behind keeps us from matching a fragment
        # of a longer word.
        r"(?P<bearer>(?<![A-Za-z])"
        r"(?P<bearer_scheme>(?:Bearer|Token|Basic)\s+)"
        r"[A-Za-z0-9+/=._\-]+)",
        lambda m: m.group("bearer_scheme") + _REDACTED,
    ),
    (
        "aws",
        # AWS access key IDs: ``AKIA`` followed by 16 base32 chars.
        # Look-arounds anchor on token-character boundaries so we do
        # not redact a fragment of a longer alphanumeric blob.
        r"(?P<aws>(?<![A-Z0-9])AKIA[A-Z0-9]{16}(?![A-Z0-9]))",
        lambda m: _REDACTED,
    ),
]


def redact(*extra_patterns):
    """Return a Loguru patcher that scrubs common secrets from log messages.

    The returned callable is suitable for :meth:`Logger.patch`. For each
    log record, the patcher rewrites ``record["message"]`` in place,
    replacing any built-in or caller-supplied secret pattern matches
    with ``"[REDACTED]"``.

    Built-in coverage: URI userinfo, HTTP ``Authorization`` headers
    and bare ``Bearer``/``Token``/``Basic`` schemes (scheme preserved,
    credential replaced); ``key=value`` / ``key: value`` for the common
    secret keys ``password``, ``token``, ``secret``, ``api_key``,
    ``apikey`` (key name preserved); AWS access key IDs (``AKIA`` + 16
    chars, whole match replaced).

    Each item in ``extra_patterns`` may be a regex source string or a
    pre-compiled regex pattern object. All patterns -- built-in plus
    extras -- are joined with ``|`` and compiled into a single regex
    once when :func:`redact` is called, so the patcher performs no
    compilation per log record. Compilation uses ``re.IGNORECASE``;
    invalid regex sources raise :class:`re.error` eagerly at call
    time rather than at log time.
    """
    sources = []
    dispatch = {}
    for name, source, replacement in _BUILTIN_PATTERNS:
        sources.append(source)
        dispatch[name] = replacement
    for index, pattern in enumerate(extra_patterns):
        # Plan note: distinguish str from compiled regex via
        # ``isinstance(x, str)`` rather than ``isinstance(x, re.Pattern)``
        # so the runtime stays compatible with Python < 3.7 (where
        # ``re.Pattern`` is not part of ``re``'s public API).
        if isinstance(pattern, str):
            source = pattern
        else:
            source = pattern.pattern
        group_name = "extra_%d" % index
        sources.append("(?P<%s>%s)" % (group_name, source))
        dispatch[group_name] = lambda m: _REDACTED

    # Single combined compilation, once per redact() call.
    combined = re.compile("|".join(sources), re.IGNORECASE)

    def replace(match):
        # Identify which top-level alternative matched. ``groupdict()``
        # returns ``None`` for groups that did not participate, so the
        # first non-None top-level entry is the winner.
        groups = match.groupdict()
        for name, replacement in dispatch.items():
            if groups.get(name) is not None:
                return replacement(match)
        # Defensive: a successful sub() with no top-level group set
        # would mean a programming error in this module. Leave the
        # text untouched rather than blowing up at log time.
        return match.group(0)

    def patcher(record):
        record["message"] = combined.sub(replace, record["message"])

    return patcher
