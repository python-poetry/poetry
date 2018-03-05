from . import toplevels
from .cascadedict import CascadeDict


class NamedDict(dict):
    """
    A dict that can use Name instances as keys.
    """

    def __init__(self, other_dict=None):
        dict.__init__(self)
        if other_dict:
            for k, v in other_dict.items():
                self[k] = v

    def __setitem__(self, key, value):
        """
        key can be an Name instance.

        When key is a path in the form of an Name instance,
        all the parents and grandparents of the value are
        created along the way as instances of NamedDict.

        If the parent of the value exists, it is replaced with a
        CascadeDict() that cascades the old parent value
        with a new NamedDict that contains the given child name and value.
        """
        if isinstance(key, toplevels.Name):
            obj = self
            for i, name in enumerate(key.sub_names):
                if name in obj:
                    if i == len(key.sub_names) - 1:
                        obj[name] = CascadeDict(obj[name], value)
                    else:
                        obj[name] = CascadeDict(NamedDict(), obj[name])
                else:
                    if i == len(key.sub_names) - 1:
                        obj[name] = value
                    else:
                        obj[name] = NamedDict()

                obj = obj[name]
        else:
            return dict.__setitem__(self, key, value)

    def __contains__(self, item):
        try:
            _ = self[item]
            return True
        except KeyError:
            return False

    def append(self, key, value):
        """
        Makes sure the value pointed to by key exists
        and is a list and appends the given value to it.
        """
        if key in self:
            self[key].append(value)
        else:
            self[key] = [value]

    def __getitem__(self, item):
        if isinstance(item, toplevels.Name):
            d = self
            for name in item.sub_names:
                d = d[name]
            return d
        else:
            return dict.__getitem__(self, item)

    def __eq__(self, other):
        return dict.__eq__(self, other)


def structure(table_toplevels):
    """
    Accepts an ordered sequence of TopLevel instances and returns a navigable
    object structure representation of the TOML file.
    """
    table_toplevels = tuple(table_toplevels)
    obj = NamedDict()

    last_array_of_tables = None  # The Name of the last array-of-tables header

    for toplevel in table_toplevels:

        if isinstance(toplevel, toplevels.AnonymousTable):
            obj[''] = toplevel.table_element

        elif isinstance(toplevel, toplevels.Table):
            if last_array_of_tables and toplevel.name.is_prefixed_with(last_array_of_tables):
                seq = obj[last_array_of_tables]
                unprefixed_name = toplevel.name.without_prefix(last_array_of_tables)

                seq[-1] = CascadeDict(seq[-1], NamedDict({unprefixed_name: toplevel.table_element}))
            else:
                obj[toplevel.name] = toplevel.table_element
        else:    # It's an ArrayOfTables

            if last_array_of_tables and toplevel.name != last_array_of_tables and \
                    toplevel.name.is_prefixed_with(last_array_of_tables):

                seq = obj[last_array_of_tables]
                unprefixed_name = toplevel.name.without_prefix(last_array_of_tables)

                if unprefixed_name in seq[-1]:
                    seq[-1][unprefixed_name].append(toplevel.table_element)
                else:
                    cascaded_with = NamedDict({unprefixed_name: [toplevel.table_element]})
                    seq[-1] = CascadeDict(seq[-1], cascaded_with)

            else:
                obj.append(toplevel.name, toplevel.table_element)
                last_array_of_tables = toplevel.name

    return obj
