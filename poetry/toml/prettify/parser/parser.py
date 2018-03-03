
"""
    A Recursive Descent implementation of a lexical parser for TOML.

    Grammar:
    --------

    Newline -> NEWLINE
    Comment -> COMMENT Newline
    LineTerminator -> Comment | Newline
    Space -> WHITESPACE Space | WHITESPACE | EMPTY
    TableHeader -> Space [ Space TableHeaderName Space ] Space LineTerminator |
        Space [[ Space TableHeaderName Space ]] Space LineTerminator
    TableHeaderName -> STRING Space '.' Space TableHeaderName | STRING
    Atomic -> STRING | INTEGER | FLOAT | DATE | BOOLEAN

    Array -> '[' Space ArrayInternal Space ']' | '[' Space ArrayInternal Space LineTerminator Space ']'
    ArrayInternal -> LineTerminator Space ArrayInternal | Value Space ',' Space LineTerminator Space ArrayInternal |
        Value Space ',' Space ArrayInternal | LineTerminator | Value | EMPTY

    InlineTable -> '{' Space InlineTableInternal Space '}'
    InlineTableKeyValuePair = STRING Space '=' Space Value
    InlineTableInternal -> InlineTableKeyValuePair Space ',' Space InlineTableInternal |
        InlineTableKeyValuePair | Empty

    Value -> Atomic | InlineTable | Array
    KeyValuePair -> Space STRING Space '=' Space Value Space LineTerminator

    TableBody -> KeyValuePair TableBody | EmptyLine TableBody | EmptyLine | KeyValuePair

    EmptyLine -> Space LineTerminator
    FileEntry -> TableHeader | TableBody

    TOMLFileElements -> FileEntry TOMLFileElements | FileEntry | EmptyLine | EMPTY
"""

from ..elements.array import ArrayElement
from ..elements.atomic import AtomicElement
from ..elements.inlinetable import InlineTableElement
from ..elements.metadata import NewlineElement, CommentElement, WhitespaceElement, PunctuationElement
from ..elements.table import TableElement
from ..elements.tableheader import TableHeaderElement
from ..tokens import TYPE_BARE_STRING
from ..tokens import TYPE_BOOLEAN
from ..tokens import TYPE_COMMENT
from ..tokens import TYPE_DATE
from ..tokens import TYPE_FLOAT
from ..tokens import TYPE_INTEGER
from ..tokens import TYPE_LITERAL_STRING
from ..tokens import TYPE_MULTILINE_LITERAL_STRING
from ..tokens import TYPE_MULTILINE_STRING
from ..tokens import TYPE_NEWLINE
from ..tokens import TYPE_OP_ASSIGNMENT
from ..tokens import TYPE_OP_COMMA
from ..tokens import TYPE_OP_CURLY_LEFT_BRACKET
from ..tokens import TYPE_OP_CURLY_RIGHT_BRACKET
from ..tokens import TYPE_OP_DOUBLE_SQUARE_LEFT_BRACKET
from ..tokens import TYPE_OP_DOUBLE_SQUARE_RIGHT_BRACKET
from ..tokens import TYPE_OP_SQUARE_LEFT_BRACKET
from ..tokens import TYPE_OP_SQUARE_RIGHT_BRACKET
from ..tokens import TYPE_OPT_DOT
from ..tokens import TYPE_STRING
from ..tokens import TYPE_WHITESPACE

from .recdesc import capture_from
from .errors import ParsingError

"""
    Non-terminals are represented as functions which return (RESULT, pending_token_stream), or raise ParsingError.
"""


def token(token_type):
    def factory(ts):
        t = ts.head
        if t.type != token_type:
            raise ParsingError('Expected a token of type {}'.format(token_type))
        return t, ts.tail
    return factory


def newline_element(token_stream):
    """
    Returns NewlineElement, pending_token_stream or raises ParsingError.
    """
    captured = capture_from(token_stream).find(token(TYPE_NEWLINE))
    return NewlineElement(captured.value()), captured.pending_tokens


def comment_tokens(ts1):
    c1 = capture_from(ts1).find(token(TYPE_COMMENT)).and_find(token(TYPE_NEWLINE))
    return c1.value(), c1.pending_tokens


def comment_element(token_stream):
    """
    Returns CommentElement, pending_token_stream or raises ParsingError.
    """
    captured = capture_from(token_stream).find(comment_tokens)
    return CommentElement(captured.value()), captured.pending_tokens


def line_terminator_tokens(token_stream):
    captured = capture_from(token_stream).find(comment_tokens).or_find(token(TYPE_NEWLINE))
    return captured.value(), captured.pending_tokens


def line_terminator_element(token_stream):
    captured = capture_from(token_stream).find(comment_element).or_find(newline_element)
    return captured.value('Expected a comment or a newline')[0], captured.pending_tokens


def zero_or_more_tokens(token_type):

    def factory(token_stream):
        def more(ts):
            c = capture_from(ts).find(token(token_type)).and_find(zero_or_more_tokens(token_type))
            return c.value(), c.pending_tokens

        def two(ts):
            c = capture_from(ts).find(token(TYPE_WHITESPACE))
            return c.value(), c.pending

        def zero(ts):
            return tuple(), ts

        captured = capture_from(token_stream).find(more).or_find(two).or_find(zero)
        return captured.value(), captured.pending_tokens

    return factory


def space_element(token_stream):
    captured = capture_from(token_stream).find(zero_or_more_tokens(TYPE_WHITESPACE))
    return WhitespaceElement([t for t in captured.value() if t]), captured.pending_tokens


def string_token(token_stream):
    captured = capture_from(token_stream).\
        find(token(TYPE_BARE_STRING)).\
        or_find(token(TYPE_STRING)).\
        or_find(token(TYPE_LITERAL_STRING)).\
        or_find(token(TYPE_MULTILINE_STRING)).\
        or_find(token(TYPE_MULTILINE_LITERAL_STRING))
    return captured.value('Expected a string'), captured.pending_tokens


def string_element(token_stream):
    captured = capture_from(token_stream).find(string_token)
    return AtomicElement(captured.value()), captured.pending_tokens


def table_header_name_tokens(token_stream):

    def one(ts):
        c = capture_from(ts).\
            find(string_token).\
            and_find(zero_or_more_tokens(TYPE_WHITESPACE)).\
            and_find(token(TYPE_OPT_DOT)).\
            and_find(zero_or_more_tokens(TYPE_WHITESPACE)).\
            and_find(table_header_name_tokens)
        return c.value(), c.pending_tokens

    captured = capture_from(token_stream).find(one).or_find(string_token)
    return captured.value(), captured.pending_tokens


def table_header_element(token_stream):

    def single(ts1):
        c1 = capture_from(ts1).\
            find(zero_or_more_tokens(TYPE_WHITESPACE)).\
            and_find(token(TYPE_OP_SQUARE_LEFT_BRACKET)).\
            and_find(zero_or_more_tokens(TYPE_WHITESPACE)).\
            and_find(table_header_name_tokens).\
            and_find(zero_or_more_tokens(TYPE_WHITESPACE)).\
            and_find(token(TYPE_OP_SQUARE_RIGHT_BRACKET)).\
            and_find(zero_or_more_tokens(TYPE_WHITESPACE)).\
            and_find(line_terminator_tokens)

        return c1.value(), c1.pending_tokens

    def double(ts2):
        c2 = capture_from(ts2).\
            find(zero_or_more_tokens(TYPE_WHITESPACE)).\
            and_find(token(TYPE_OP_DOUBLE_SQUARE_LEFT_BRACKET)).\
            and_find(zero_or_more_tokens(TYPE_WHITESPACE)).\
            and_find(table_header_name_tokens).\
            and_find(zero_or_more_tokens(TYPE_WHITESPACE)).\
            and_find(token(TYPE_OP_DOUBLE_SQUARE_RIGHT_BRACKET)).\
            and_find(zero_or_more_tokens(TYPE_WHITESPACE)).\
            and_find(line_terminator_tokens)

        return c2.value(), c2.pending_tokens

    captured = capture_from(token_stream).find(single).or_find(double)
    return TableHeaderElement(captured.value()), captured.pending_tokens


def atomic_element(token_stream):
    captured = capture_from(token_stream).\
        find(string_token).\
        or_find(token(TYPE_INTEGER)).\
        or_find(token(TYPE_FLOAT)).\
        or_find(token(TYPE_DATE)).\
        or_find(token(TYPE_BOOLEAN))
    return AtomicElement(captured.value('Expected an atomic primitive value')), captured.pending_tokens


def punctuation_element(token_type):
    def factory(ts):
        c = capture_from(ts).find(token(token_type))
        return PunctuationElement(c.value('Expected the punctuation element: {}'.format(token_type))), c.pending_tokens
    return factory


def value(token_stream):
    captured = capture_from(token_stream).\
        find(atomic_element).\
        or_find(array_element).\
        or_find(inline_table_element)
    return captured.value('Expected a primitive value, array or an inline table'), captured.pending_tokens


def array_internal(ts):

    def zero(ts0):
        c = capture_from(ts0).\
            and_find(line_terminator_element).\
            and_find(space_element).\
            and_find(array_internal)
        return c.value(), c.pending_tokens

    def one(ts1):
        c = capture_from(ts1).\
            find(value).\
            and_find(space_element).\
            and_find(punctuation_element(TYPE_OP_COMMA)).\
            and_find(space_element).\
            and_find(line_terminator_element).\
            and_find(space_element).\
            and_find(array_internal)
        return c.value(), c.pending_tokens

    def two(ts2):
        c = capture_from(ts2).\
            find(value).\
            and_find(space_element).\
            and_find(punctuation_element(TYPE_OP_COMMA)).\
            and_find(space_element).\
            and_find(array_internal)
        return c.value(), c.pending_tokens

    def three(ts3):
        c = capture_from(ts3).\
            find(space_element).\
            and_find(line_terminator_element)
        return c.value(), c.pending_tokens

    captured = capture_from(ts).find(zero).or_find(one).or_find(two).or_find(three).or_find(value).or_empty()
    return captured.value(), captured.pending_tokens


def array_element(token_stream):

    def one(ts1):
        ca = capture_from(ts1).\
            find(punctuation_element(TYPE_OP_SQUARE_LEFT_BRACKET)).\
            and_find(space_element).\
            and_find(array_internal).\
            and_find(space_element).\
            and_find(punctuation_element(TYPE_OP_SQUARE_RIGHT_BRACKET))
        return ca.value(), ca.pending_tokens

    def two(ts2):
        ca = capture_from(ts2).\
            find(punctuation_element(TYPE_OP_SQUARE_LEFT_BRACKET)).\
            and_find(space_element).\
            and_find(array_internal).\
            and_find(space_element).\
            and_find(line_terminator_element).\
            and_find(space_element).\
            and_find(punctuation_element(TYPE_OP_SQUARE_RIGHT_BRACKET))
        return ca.value(), ca.pending_tokens

    captured = capture_from(token_stream).find(one).or_find(two)
    return ArrayElement(captured.value()), captured.pending_tokens


def inline_table_element(token_stream):
    # InlineTableElement -> '{' Space InlineTableInternal Space '}'
    # InlineTableKeyValuePair = STRING Space '=' Space Value
    # InlineTableInternal -> InlineTableKeyValuePair Space ',' Space InlineTableInternal |
    #     InlineTableKeyValuePair | Empty
    def key_value(ts):
        ca = capture_from(ts).\
            find(string_element).\
            and_find(space_element).\
            and_find(punctuation_element(TYPE_OP_ASSIGNMENT)).\
            and_find(space_element).\
            and_find(value)
        return ca.value(), ca.pending_tokens

    def internal(ts):
        def one(ts1):
            c1 = capture_from(ts1).\
                find(key_value).\
                and_find(space_element).\
                and_find(punctuation_element(TYPE_OP_COMMA)).\
                and_find(space_element).\
                and_find(internal)
            return c1.value(), c1.pending_tokens

        c = capture_from(ts).find(one).or_find(key_value).or_empty()
        return c.value(), c.pending_tokens

    captured = capture_from(token_stream).\
        find(punctuation_element(TYPE_OP_CURLY_LEFT_BRACKET)).\
        and_find(space_element).\
        and_find(internal).\
        and_find(space_element).\
        and_find(punctuation_element(TYPE_OP_CURLY_RIGHT_BRACKET))

    return InlineTableElement(captured.value()), captured.pending_tokens


def key_value_pair(token_stream):
    captured = capture_from(token_stream).\
        find(space_element).\
        and_find(string_element).\
        and_find(space_element).\
        and_find(punctuation_element(TYPE_OP_ASSIGNMENT)).\
        and_find(space_element).\
        and_find(value).\
        and_find(space_element).\
        and_find(line_terminator_element)
    return captured.value(), captured.pending_tokens


def table_body_elements(token_stream):
    # TableBody -> KeyValuePair TableBody | EmptyLine TableBody | EmptyLine | KeyValuePair
    def one(ts1):
        c = capture_from(ts1).\
            find(key_value_pair).\
            and_find(table_body_elements)
        return c.value(), c.pending_tokens

    def two(ts2):
        c = capture_from(ts2).\
            find(empty_line_elements).\
            and_find(table_body_elements)
        return c.value(), c.pending_tokens

    captured = capture_from(token_stream).\
        find(one).\
        or_find(two).\
        or_find(empty_line_elements).\
        or_find(key_value_pair)

    return captured.value(), captured.pending_tokens


def table_body_element(token_stream):
    captured = capture_from(token_stream).find(table_body_elements)
    return TableElement(captured.value()), captured.pending_tokens


def empty_line_tokens(ts1):
    c1 = capture_from(ts1).find(space_element).and_find(line_terminator_element)
    return c1.value(), c1.pending_tokens


def empty_line_elements(token_stream):
    captured = capture_from(token_stream).find(empty_line_tokens)
    return captured.value(), captured.pending_tokens


def file_entry_element(token_stream):
    captured = capture_from(token_stream).find(table_header_element).\
        or_find(table_body_element)
    return captured.value(), captured.pending_tokens


def toml_file_elements(token_stream):

    def one(ts1):
        c1 = capture_from(ts1).find(file_entry_element).and_find(toml_file_elements)
        return c1.value(), c1.pending_tokens

    captured = capture_from(token_stream).find(one).or_find(file_entry_element).or_empty()
    return captured.value(), captured.pending_tokens
