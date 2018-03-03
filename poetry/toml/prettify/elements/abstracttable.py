from .common import ContainerElement
from . import traversal


class AbstractTable(ContainerElement, traversal.TraversalMixin, dict):
    """
    Common code for handling tables as key-value pairs
    with metadata elements sprinkled all over.

    Assumes input sub_elements are correct.
    """

    def __init__(self, sub_elements):
        ContainerElement.__init__(self, sub_elements)
        self._fallback = None

    def _enumerate_items(self):
        """
        Returns ((key_index, key_element), (value_index, value_element))
        for all the element key-value pairs.
        """
        non_metadata = self._enumerate_non_metadata_sub_elements()
        while True:
            yield next(non_metadata), next(non_metadata)

    def items(self):
        for (key_i, key), (value_i, value) in self._enumerate_items():
            yield key.value, value.value
        if self._fallback:
            for key, value in self._fallback.items():
                yield key, value

    def keys(self):
        return tuple(key for (key, _) in self.items())

    def values(self):
        return tuple(value for (_, value) in self.items())

    def __len__(self):
        return len(tuple(self._enumerate_items()))

    def __contains__(self, item):
        return item in self.keys()

    def _find_key_and_value(self, key):
        """
        Returns (key_i, value_i) corresponding to the given key value.

        Raises KeyError if no matching key found.
        """
        for (key_i, key_element), (value_i, value_element) in self._enumerate_items():
            if key_element.value == key:
                return key_i, value_i
        raise KeyError

    def __getitem__(self, item):
        for key, value in self.items():
            if key == item:
                return value
        raise KeyError

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def set_fallback(self, fallback):
        """
        Sets a fallback dict-like instance to be used to look up values after they are not found
        in this instance.
        """
        self._fallback = fallback

    @property
    def primitive_value(self):
        """
        Returns a primitive Python value without any formatting or markup metadata.
        """
        return {
            key:
                value.primitive_value if hasattr(value, 'primitive_value') else value for key, value in self.items()
            }
