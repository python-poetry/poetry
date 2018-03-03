from . import factory, traversal
from .common import Element, ContainerElement
from .factory import create_element
from .metadata import NewlineElement
from .errors import InvalidElementError


class ArrayElement(ContainerElement, traversal.TraversalMixin, list):
    """
    A sequence-like container element containing other atomic elements or other containers.

    Implements list-like interface.

    Assumes input sub_elements are correct for an array element.

    Raises an InvalidElementError if contains heterogeneous values.
    """

    def __init__(self, sub_elements):
        super(ArrayElement, self).__init__(sub_elements)
        self._check_homogeneity()

    def _check_homogeneity(self):
        if len(set(type(v) for v in self.primitive_value)) > 1:
            raise InvalidElementError('Array should be homogeneous')

    def __len__(self):
        return len(tuple(self._enumerate_non_metadata_sub_elements()))

    def __getitem__(self, i):
        """
        Returns the ith entry, which can be a primitive value, a seq-lie, or a dict-like object.
        """
        return self._find_value(i)[1].value

    def __setitem__(self, i, value):
        value_i, _ = self._find_value(i)
        new_element = value if isinstance(value, Element) else factory.create_element(value)
        self._sub_elements = self.sub_elements[:value_i] + [new_element] + self.sub_elements[value_i+1:]

    @property
    def value(self):
        return self     # self is a sequence-like value

    @property
    def primitive_value(self):
        """
        Returns a primitive Python value without any formatting or markup metadata.
        """
        return list(
            self[i].primitive_value if hasattr(self[i], 'primitive_value')
            else self[i]
            for i in range(len(self)))

    def __str__(self):
        return "{}".format(self.primitive_value)

    def __repr__(self):
        return "Array{}".format(str(self))

    def append(self, v):
        new_entry = [create_element(v)]

        if self:    # If not empty, we need a comma and whitespace prefix!
            new_entry = [
                factory.create_operator_element(','),
                factory.create_whitespace_element(),
            ] + new_entry

        insertion_index = self._find_closing_square_bracket()
        self._sub_elements = self._sub_elements[:insertion_index] + new_entry + \
                             self._sub_elements[insertion_index:]

    def _find_value(self, i):
        """
        Returns (value_index, value) of ith value in this sequence.

        Raises IndexError if not found.
        """
        return tuple(self._enumerate_non_metadata_sub_elements())[i]

    def __delitem__(self, i):
        value_i, value = self._find_value(i)

        begin, end = value_i, value_i+1

        # Rules:
        #   1. begin should be index to the preceding comma to the value
        #   2. end should be index to the following comma, or the closing bracket
        #   3. If no preceding comma found but following comma found then end should be the index of the following value

        preceding_comma = self._find_preceding_comma(value_i)
        found_preceding_comma = preceding_comma >= 0
        if found_preceding_comma:
            begin = preceding_comma

        following_comma = self._find_following_comma(value_i)
        if following_comma >= 0:
            if not found_preceding_comma:
                end = self._find_following_non_metadata(following_comma)
            else:
                end = following_comma
        else:
            end = self._find_following_closing_square_bracket(0)

        self._sub_elements = self.sub_elements[:begin] + self._sub_elements[end:]

    @property
    def is_multiline(self):
        return any(isinstance(e, (NewlineElement)) for e in self.elements)

    def turn_into_multiline(self):
        """
        Turns this array into a multi-line array with each element lying on its own line.
        """
        if self.is_multiline:
            return

        i = self._find_following_comma(-1)

        def next_entry_i():
            return self._find_following_non_metadata(i)

        def next_newline_i():
            return self._find_following_newline(i)

        def next_closing_bracket_i():
            return self._find_following_closing_square_bracket(i)

        def next_comma_i():
            return self._find_following_comma(i)

        while i < len(self.elements)-1:
            if next_newline_i() < next_entry_i():
                self.elements.insert(i+1, factory.create_newline_element())
                if float('-inf') < next_comma_i() < next_closing_bracket_i():
                    i = next_comma_i()
                else:
                    i = next_closing_bracket_i()
