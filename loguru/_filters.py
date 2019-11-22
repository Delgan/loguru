def filter_none(record):
    return record["name"] is not None


def filter_by_name(record, parent, length):
    name = record["name"]
    if name is None:
        return False
    return (name + ".")[:length] == parent


def filter_by_level(record, level_per_module):
    name = record["name"]

    level = 0

    if name in level_per_module:
        level = level_per_module[name]
    elif name is not None:
        lookup = ""
        if "" in level_per_module:
            level = level_per_module[""]
        for n in name.split("."):
            lookup += n
            if lookup in level_per_module:
                level = level_per_module[lookup]
            lookup += "."

    if level is False:
        return False

    return record["level"].no >= level
