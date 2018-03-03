from .prettify.errors import NoArrayFoundError
from . import structurer, toplevels, raw
from .array import ArrayOfTables
from .freshtable import FreshTable

from .prettify.elements import factory as element_factory
from .prettify import util


class TOMLFile(dict):
    """
    A TOMLFile object that tries its best to prserve formatting and order of mappings of the input source.

    Raises InvalidTOMLFileError on invalid input elements.

    Raises DuplicateKeysError, DuplicateTableError when appropriate.
    """

    def __init__(self, _elements):
        self._elements = []
        self._navigable = {}
        self.append_elements(_elements)

    def __getitem__(self, item):
        try:
            value = self._navigable[item]
            if isinstance(value, (list, tuple)):
                return ArrayOfTables(toml_file=self, name=item, iterable=value)
            else:
                return value
        except KeyError:
            return FreshTable(parent=self, name=item, is_array=False)

    def __contains__(self, item):
        return item in self.keys()

    def _setitem_with_key_seq(self, key_seq, value):
        """
        Sets a the value in the TOML file located by the given key sequence.

        Example:
        self._setitem(('key1', 'key2', 'key3'), 'text_value')
        is equivalent to doing
        self['key1']['key2']['key3'] = 'text_value'
        """
        table = self
        key_so_far = tuple()
        for key in key_seq[:-1]:
            key_so_far += (key,)
            self._make_sure_table_exists(key_so_far)
            table = table[key]
        table[key_seq[-1]] = value

    def _array_setitem_with_key_seq(self, array_name, index, key_seq, value):
        """
        Sets a the array value in the TOML file located by the given key sequence.

        Example:
        self._array_setitem(array_name, index, ('key1', 'key2', 'key3'), 'text_value')
        is equivalent to doing
        self.array(array_name)[index]['key1']['key2']['key3'] = 'text_value'
        """
        table = self.array(array_name)[index]
        key_so_far = tuple()
        for key in key_seq[:-1]:
            key_so_far += (key,)
            new_table = self._array_make_sure_table_exists(array_name, index, key_so_far)
            if new_table is not None:
                table = new_table
            else:
                table = table[key]
        table[key_seq[-1]] = value

    def _make_sure_table_exists(self, name_seq):
        """
        Makes sure the table with the full name comprising of name_seq exists.
        """
        t = self
        for key in name_seq[:-1]:
            t = t[key]
        name = name_seq[-1]
        if name not in t:
            self.append_elements([element_factory.create_table_header_element(name_seq),
                                  element_factory.create_table({})])

    def _array_make_sure_table_exists(self, array_name, index, name_seq):
        """
        Makes sure the table with the full name comprising of name_seq exists.
        """
        t = self[array_name][index]
        for key in name_seq[:-1]:
            t = t[key]
        name = name_seq[-1]
        if name not in t:
            new_table = element_factory.create_table({})
            self.append_elements([element_factory.create_table_header_element((array_name,) + name_seq), new_table])
            return new_table

    def __delitem__(self, key):
        table_element_index = self._elements.index(self._navigable[key])
        self._elements[table_element_index] = element_factory.create_table({})
        self._on_element_change()

    def __setitem__(self, key, value):

        # Setting an array-of-tables
        if key and isinstance(value, (tuple, list)) and value and all(isinstance(v, dict) for v in value):
            for table in value:
                self.array(key).append(table)

        # Or setting a whole single table
        elif isinstance(value, dict):

            if key and key in self:
                del self[key]

            for key_seq, child_value in util.flatten_nested({key: value}).items():
                self._setitem_with_key_seq(key_seq, child_value)

            # if key in self._navigable:
            #     del self[key]
            #     index = self._elements.index(self._navigable[key])
            #     self._elements = self._elements[:index] + [element_factory.create_table(value)] + self._elements[index+1:]
            # else:
            #     if key:
            #         self._elements.append(element_factory.create_table_header_element(key))
            #     self._elements.append(element_factory.create_table(value))


        # Or updating the anonymous section table
        else:
            # It's mea
            self[''][key] = value

        self._on_element_change()

    def _detect_toplevels(self):
        """
        Returns a sequence of TopLevel instances for the current state of this table.
        """
        return tuple(e for e in toplevels.identify(self.elements) if isinstance(e, toplevels.Table))

    def _update_table_fallbacks(self, table_toplevels):
        """
        Updates the fallbacks on all the table elements to make relative table access possible.

        Raises DuplicateKeysError if appropriate.
        """

        if len(self.elements) <= 1:
            return

        def parent_of(toplevel):
            # Returns an TopLevel parent of the given entry, or None.
            for parent_toplevel in table_toplevels:
                if toplevel.name.sub_names[:-1] == parent_toplevel.name.sub_names:
                    return parent_toplevel

        for entry in table_toplevels:
            if entry.name.is_qualified:
                parent = parent_of(entry)
                if parent:
                    child_name = entry.name.without_prefix(parent.name)
                    parent.table_element.set_fallback({child_name.sub_names[0]: entry.table_element})

    def _recreate_navigable(self):
        if self._elements:
            self._navigable = structurer.structure(toplevels.identify(self._elements))

    def array(self, name):
        """
        Returns the array of tables with the given name.
        """
        if name in self._navigable:
            if isinstance(self._navigable[name], (list, tuple)):
                return self[name]
            else:
                raise NoArrayFoundError
        else:
            return ArrayOfTables(toml_file=self, name=name)

    def _on_element_change(self):
        self._recreate_navigable()

        table_toplevels = self._detect_toplevels()
        self._update_table_fallbacks(table_toplevels)

    def append_elements(self, elements):
        """
        Appends more elements to the contained internal elements.
        """
        self._elements = self._elements + list(elements)
        self._on_element_change()

    def prepend_elements(self, elements):
        """
        Prepends more elements to the contained internal elements.
        """
        self._elements = list(elements) + self._elements
        self._on_element_change()

    def dumps(self):
        """
        Returns the TOML file serialized back to str.
        """
        return ''.join(element.serialized() for element in self._elements)

    def dump(self, file_path):
        with open(file_path, mode='w') as fp:
            fp.write(self.dumps())

    def keys(self):
        return set(self._navigable.keys()) | {''}

    def values(self):
        return self._navigable.values()

    def items(self):
        items = list(self._navigable.items())

        def has_anonymous_entry():
            return any(key == '' for (key, _) in items)

        if has_anonymous_entry():
            return items
        else:
            return items + [('', self[''])]

    def get(self, item, default=None):
        return self._navigable.get(item, default)

    @property
    def primitive(self):
        """
        Returns a primitive object representation for this container (which is a dict).

        WARNING: The returned container does not contain any markup or formatting metadata.
        """
        raw_container = raw.to_raw(self._navigable)

        # Collapsing the anonymous table onto the top-level container is present
        if '' in raw_container:
            raw_container.update(raw_container[''])
            del raw_container['']

        return raw_container

    def append_fresh_table(self, fresh_table):
        """
        Gets called by FreshTable instances when they get written to.
        """
        if fresh_table.name:
            elements = []
            if fresh_table.is_array:
                elements += [element_factory.create_array_of_tables_header_element(fresh_table.name)]
            else:
                elements += [element_factory.create_table_header_element(fresh_table.name)]

            elements += [fresh_table, element_factory.create_newline_element()]
            self.append_elements(elements)

        else:
            # It's an anonymous table
            self.prepend_elements([fresh_table, element_factory.create_newline_element()])

    @property
    def elements(self):
        return self._elements

    def __str__(self):

        is_empty = (not self['']) and (not tuple(k for k in self.keys() if k))

        def key_name(key):
            return '[ANONYMOUS]' if not key else key

        def pair(key, value):
            return '%s = %s' % (key_name(key), str(value))

        content_text = '' if is_empty else \
            '\n\t' + ',\n\t'.join(pair(k, v) for (k, v) in self.items() if v) + '\n'

        return "TOMLFile{%s}" % content_text

    def __repr__(self):
        return str(self)



