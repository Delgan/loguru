def filter_none(record):
    """Determine whether a log record should pass based on its logger name.

    Parameters
    ----------
    record : dict
        The log record dictionary containing at least a ``"name"`` key.

    Returns
    -------
    bool
        ``True`` if the record's ``"name"`` is not ``None``, ``False`` otherwise.
    """
    return record["name"] is not None


def filter_by_name(record, parent, length):
    """Determine whether a log record's name matches a given parent module prefix.

    Parameters
    ----------
    record : dict
        The log record dictionary containing at least a ``"name"`` key.
    parent : str
        The parent module name to match against, expected to end with ``"."``.
    length : int
        The number of characters to compare, typically ``len(parent)``.

    Returns
    -------
    bool
        ``True`` if the record name starts with the parent prefix, ``False`` otherwise.
    """
    name = record["name"]
    if name is None:
        return False
    return (name + ".")[:length] == parent


def filter_by_level(record, level_per_module):
    """Determine whether a log record meets the minimum level for its module.

    The level is looked up by walking up the module hierarchy until a match is
    found in ``level_per_module``. A value of ``False`` explicitly disables the
    module; any other truthy numeric value sets the minimum level number.

    Parameters
    ----------
    record : dict
        The log record dictionary containing ``"name"`` and ``"level"`` keys.
    level_per_module : dict
        Mapping of module name to minimum level number, or ``False`` to disable.

    Returns
    -------
    bool
        ``True`` if the record's level meets or exceeds the configured minimum,
        ``False`` if the module is explicitly disabled or the level is too low.
    """
    name = record["name"]

    while True:
        level = level_per_module.get(name, None)
        if level is False:
            return False
        if level is not None:
            return record["level"].no >= level
        if not name:
            return True
        index = name.rfind(".")
        name = name[:index] if index != -1 else ""
