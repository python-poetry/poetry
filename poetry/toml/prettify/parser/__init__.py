
"""
    A parser for TOML tokens into TOML elements.
"""

from .elementsanitizer import sanitize
from .errors import ParsingError
from .parser import toml_file_elements
from .tokenstream import TokenStream


def parse_tokens(tokens):
    """
    Parses the given token sequence into a sequence of top-level TOML elements.

    Raises ParserError on invalid TOML input.
    """
    return _parse_token_stream(TokenStream(tokens))


def _parse_token_stream(token_stream):
    """
    Parses the given token_stream into a sequence of top-level TOML elements.

    Raises ParserError on invalid input TOML.
    """
    elements, pending = toml_file_elements(token_stream)

    if not pending.at_end:
        raise ParsingError('Failed to parse line {}'.format(pending.head.row))

    return sanitize(elements)
