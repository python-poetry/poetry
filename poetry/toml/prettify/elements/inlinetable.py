from . import factory, abstracttable
from .common import Element


class InlineTableElement(abstracttable.AbstractTable):
    """
    An Element containing key-value pairs, representing an inline table.

    Implements dict-like interface.

    Assumes input sub_elements are correct for an inline table element.
    """

    def __init__(self, sub_elements):
        abstracttable.AbstractTable.__init__(self, sub_elements)

    def __setitem__(self, key, value):

        new_element = value if isinstance(value, Element) else factory.create_element(value)

        try:

            key_i, value_i = self._find_key_and_value(key)
            # Found, then replace the value element with a new one
            self._sub_elements = self.sub_elements[:value_i] + [new_element] + self.sub_elements[value_i+1:]

        except KeyError:    # Key does not exist, adding anew!

            new_entry = [
                factory.create_string_element(key, bare_allowed=True),
                factory.create_whitespace_element(),
                factory.create_operator_element('='),
                factory.create_whitespace_element(),
                new_element,
            ]

            if self:    # If not empty
                new_entry = [
                    factory.create_operator_element(','),
                    factory.create_whitespace_element(),
                ] + new_entry

            insertion_index = self._find_closing_curly_bracket()
            self._sub_elements = self.sub_elements[:insertion_index] + new_entry + self.sub_elements[insertion_index:]

    def __delitem__(self, key):

        key_i, value_i = self._find_key_and_value(key)

        begin, end = key_i, value_i+1

        # Rules:
        #   1. begin should be index to the preceding comma to the key
        #   2. end should be index to the following comma, or the closing bracket
        #   3. If no preceding comma found but following comma found then end should be the index of the following key

        preceding_comma = self._find_preceding_comma(begin)
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
            end = self._find_closing_curly_bracket()

        self._sub_elements = self.sub_elements[:begin] + self.sub_elements[end:]

    def multiline_equivalent(self):
        return factory.create_inline_table(self.primitive_value, multiline_table=True, multiline_strings_allowed=True)

    @property
    def value(self):
        return self     # self is a dict-like value that is perfectly usable
