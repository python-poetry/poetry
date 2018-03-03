from .prettify.errors import InvalidValueError
from .freshtable import FreshTable
from .prettify import util


class ArrayOfTables(list):

    def __init__(self, toml_file, name, iterable=None):
        if iterable:
            list.__init__(self, iterable)
        self._name = name
        self._toml_file = toml_file

    def append(self, value):
        if isinstance(value, dict):
            table = FreshTable(parent=self, name=self._name, is_array=True)
            table._append_to_parent()
            index = len(self._toml_file[self._name]) - 1
            for key_seq, value in util.flatten_nested(value).items():
                # self._toml_file._setitem_with_key_seq((self._name, index) + key_seq, value)
                self._toml_file._array_setitem_with_key_seq(self._name, index, key_seq, value)
            # for k, v in value.items():
            #     table[k] = v
        else:
            raise InvalidValueError('Can only append a dict to an array of tables')

    def __getitem__(self, item):
        try:
            return list.__getitem__(self, item)
        except IndexError:
            if item == len(self):
                return FreshTable(parent=self, name=self._name, is_array=True)
            else:
                raise

    def append_fresh_table(self, fresh_table):
        list.append(self, fresh_table)
        if self._toml_file:
            self._toml_file.append_fresh_table(fresh_table)
