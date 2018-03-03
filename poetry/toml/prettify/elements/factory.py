import datetime
import six

from .. import tokens
from ..tokens import py2toml
from ..util import join_with
from .atomic import AtomicElement
from .metadata import PunctuationElement, WhitespaceElement, NewlineElement
from .tableheader import TableHeaderElement


def create_element(value, multiline_strings_allowed=True):
    """
    Creates and returns the appropriate elements.Element instance from the given Python primitive, sequence-like,
    or dict-like value.
    """
    from .array import ArrayElement

    if isinstance(value, (int, float, bool, datetime.datetime, datetime.date) + six.string_types) or value is None:
        primitive_token = py2toml.create_primitive_token(value, multiline_strings_allowed=multiline_strings_allowed)
        return AtomicElement((primitive_token,))

    elif isinstance(value, (list, tuple)):
        preamble = [create_operator_element('[')]
        postable = [create_operator_element(']')]
        stuffing_elements = [create_element(v) for v in value]
        spaced_stuffing = join_with(stuffing_elements,
                                    separator=[create_operator_element(','), create_whitespace_element()])

        return ArrayElement(preamble + spaced_stuffing + postable)

    elif isinstance(value, dict):
        return create_inline_table(value, multiline_table=False, multiline_strings_allowed=multiline_strings_allowed)

    else:
        raise RuntimeError('Value type unaccounted for: {} of type {}'.format(value, type(value)))


def create_inline_table(from_dict, multiline_table=False, multiline_strings_allowed=True):
    """
    Creates an InlineTable element from the given dict instance.
    """

    from .inlinetable import InlineTableElement

    preamble = [create_operator_element('{')]
    postable = [create_operator_element('}')]

    stuffing_elements = (
        (
            create_string_element(k, bare_allowed=True),
            create_whitespace_element(),
            create_operator_element('='),
            create_whitespace_element(),
            create_element(v, multiline_strings_allowed=False)
        ) for (k, v) in from_dict.items())

    pair_separator = [create_operator_element(','),
                      create_newline_element() if multiline_table else create_whitespace_element()]
    spaced_elements = join_with(stuffing_elements, separator=pair_separator)

    return InlineTableElement(preamble + spaced_elements + postable)


def create_string_element(value, bare_allowed=False):
    """
    Creates and returns an AtomicElement wrapping a string value.
    """
    return AtomicElement((py2toml.create_string_token(value, bare_allowed),))


def create_operator_element(operator):
    """
    Creates a PunctuationElement instance containing an operator token of the specified type. The operator
    should be a TOML source str.
    """
    operator_type_map = {
        ',': tokens.TYPE_OP_COMMA,
        '=': tokens.TYPE_OP_ASSIGNMENT,
        '[': tokens.TYPE_OP_SQUARE_LEFT_BRACKET,
        ']': tokens.TYPE_OP_SQUARE_RIGHT_BRACKET,
        '[[': tokens.TYPE_OP_DOUBLE_SQUARE_LEFT_BRACKET,
        ']]': tokens.TYPE_OP_DOUBLE_SQUARE_RIGHT_BRACKET,
        '{': tokens.TYPE_OP_CURLY_LEFT_BRACKET,
        '}': tokens.TYPE_OP_CURLY_RIGHT_BRACKET,
    }

    ts = (tokens.Token(operator_type_map[operator], operator),)
    return PunctuationElement(ts)


def create_newline_element():
    """
    Creates and returns a single NewlineElement.
    """
    ts = (tokens.Token(tokens.TYPE_NEWLINE, '\n'),)
    return NewlineElement(ts)


def create_whitespace_element(length=1, char=' '):
    """
    Creates and returns a WhitespaceElement containing spaces.
    """
    ts = (tokens.Token(tokens.TYPE_WHITESPACE, char),) * length
    return WhitespaceElement(ts)


def create_table_header_element(names):

    name_elements = []

    if isinstance(names, six.string_types):
        name_elements = [py2toml.create_string_token(names, bare_string_allowed=True)]
    else:
        for (i, name) in enumerate(names):
            name_elements.append(py2toml.create_string_token(name, bare_string_allowed=True))
            if i < (len(names)-1):
                name_elements.append(py2toml.operator_token(tokens.TYPE_OPT_DOT))

    return TableHeaderElement(
        [py2toml.operator_token(tokens.TYPE_OP_SQUARE_LEFT_BRACKET)] + name_elements +
        [py2toml.operator_token(tokens.TYPE_OP_SQUARE_RIGHT_BRACKET), py2toml.operator_token(tokens.TYPE_NEWLINE)],
    )


def create_array_of_tables_header_element(name):
    return TableHeaderElement((
        py2toml.operator_token(tokens.TYPE_OP_DOUBLE_SQUARE_LEFT_BRACKET),
        py2toml.create_string_token(name, bare_string_allowed=True),
        py2toml.operator_token(tokens.TYPE_OP_DOUBLE_SQUARE_RIGHT_BRACKET),
        py2toml.operator_token(tokens.TYPE_NEWLINE),
    ))


def create_table(dict_value):
    """
    Creates a TableElement out of a dict instance.
    """
    from .table import TableElement

    if not isinstance(dict_value, dict):
        raise ValueError('input must be a dict instance.')

    table_element = TableElement([create_newline_element()])
    for k, v in dict_value.items():
        table_element[k] = create_element(v)

    return table_element


def create_multiline_string(text, maximum_line_length):
    return AtomicElement(_tokens=[py2toml.create_multiline_string(text, maximum_line_length)])
