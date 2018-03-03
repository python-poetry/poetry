from .prettify.elements.table import TableElement


class FreshTable(TableElement):
    """
    A fresh TableElement that appended itself to each of parents when it first gets written to at most once.

    parents is a sequence of objects providing an append_fresh_table(TableElement) method
    """

    def __init__(self, parent, name, is_array=False):
        TableElement.__init__(self, sub_elements=[])

        self._parent = parent
        self._name = name
        self._is_array = is_array

        # As long as this flag is false, setitem() operations will append the table header and this table
        # to the toml_file's elements
        self.__appended = False

    @property
    def name(self):
        return self._name

    @property
    def is_array(self):
        return self._is_array

    def _append_to_parent(self):
        """
        Causes this ephemeral table to be persisted on the TOMLFile.
        """

        if self.__appended:
            return

        if self._parent is not None:
            self._parent.append_fresh_table(self)

        self.__appended = True

    def __setitem__(self, key, value):
        TableElement.__setitem__(self, key, value)
        self._append_to_parent()
