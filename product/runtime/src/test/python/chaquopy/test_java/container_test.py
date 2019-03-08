from types import MappingProxyType


# A read-write and read-only version is provided of each container type.


def new_list(*args):
    return list(args)

def new_list_ro(*args):
    return tuple(args)


def new_map(*args):
    assert len(args) % 2 == 0, args
    result = {}
    for i, arg in enumerate(args):
        if i % 2 == 0:
            key = arg
        else:
            result[key] = arg
    return result

def new_map_ro(*args):
    return MappingProxyType(new_map(*args))


def new_set(*args):
    return set(args)

def new_set_ro(*args):
    return frozenset(args)
