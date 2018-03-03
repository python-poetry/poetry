from ..elements import TYPE_METADATA
from ..elements.table import TableElement
from ..elements.tableheader import TableHeaderElement
from ..errors import InvalidTOMLFileError
from ..util import PeekableIterator


def sanitize(_elements):
    """
    Finds TableHeader elements that are not followed by TableBody elements
    and inserts empty TableElement right after those.
    """

    output = list(_elements)

    def find_next_table_header(after=-1):
        return next((i for (i, element) in enumerate(output)
                     if i > after and isinstance(element, TableHeaderElement)), float('-inf'))

    def find_next_table_body(after=-1):
        return next((i for (i, element) in enumerate(output)
                     if i > after and isinstance(element, TableElement)), float('-inf'))

    next_table_header_i = find_next_table_header()
    while next_table_header_i >= 0:

        following_table_header_i = find_next_table_header(next_table_header_i)
        following_table_body_i = find_next_table_body(next_table_header_i)

        if (following_table_body_i < 0) or \
                (following_table_header_i >= 0 and (following_table_header_i < following_table_body_i)):
            output.insert(next_table_header_i+1, TableElement(tuple()))

        next_table_header_i = find_next_table_header(next_table_header_i)

    return output


def validate_sanitized(_elements):
    # Non-metadata elements must start with an optional TableElement,
    # followed by zero or more (TableHeaderElement, TableElement) pairs.

    if not _elements:
        return

    it = PeekableIterator(e for e in _elements if e.type != TYPE_METADATA)

    if isinstance(it.peek(), TableElement):
        it.next()

    while it.peek():
        if not isinstance(it.peek(), TableHeaderElement):
            raise InvalidTOMLFileError
        it.next()
        if not isinstance(it.peek(), TableElement):
            raise InvalidTOMLFileError
        it.next()
