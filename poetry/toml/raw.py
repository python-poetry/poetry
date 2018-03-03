from .prettify.elements.abstracttable import AbstractTable


def to_raw(x):
    from .cascadedict import CascadeDict

    if isinstance(x, AbstractTable):
        return x.primitive_value
    elif isinstance(x, CascadeDict):
        return x.neutralized
    elif isinstance(x, (list, tuple)):
        return [to_raw(y) for y in x]
    elif isinstance(x, dict):
        return {k: to_raw(v) for (k, v) in x.items()}
    else:
        return x
