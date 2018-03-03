
"""
A regular expression based Lexer/tokenizer for TOML.
"""

from collections import namedtuple
import re
from .. import tokens
from ..errors import TOMLError

TokenSpec = namedtuple('TokenSpec', ('type', 're'))

# Specs of all the valid tokens
_LEXICAL_SPECS = (
    TokenSpec(tokens.TYPE_COMMENT, re.compile(r'^(#.*)\n')),
    TokenSpec(tokens.TYPE_STRING, re.compile(r'^("(([^"]|\\")+?[^\\]|([^"]|\\")|)")')),                       # Single line only
    TokenSpec(tokens.TYPE_MULTILINE_STRING, re.compile(r'^(""".*?""")', re.DOTALL)),
    TokenSpec(tokens.TYPE_LITERAL_STRING, re.compile(r"^('.*?')")),
    TokenSpec(tokens.TYPE_MULTILINE_LITERAL_STRING, re.compile(r"^('''.*?''')", re.DOTALL)),
    TokenSpec(tokens.TYPE_BARE_STRING, re.compile(r'^([A-Za-z0-9_-]+)')),
    TokenSpec(tokens.TYPE_DATE, re.compile(
        r'^([0-9]{4}-[0-9]{2}-[0-9]{2}(T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]*)?)?(([zZ])|((\+|-)[0-9]{2}:[0-9]{2}))?)')),
    TokenSpec(tokens.TYPE_WHITESPACE, re.compile(r'^( |\t)', re.DOTALL)),
    TokenSpec(tokens.TYPE_INTEGER, re.compile(r'^(((\+|-)[0-9_]+)|([0-9][0-9_]*))')),
    TokenSpec(tokens.TYPE_FLOAT,
              re.compile(r'^((((\+|-)[0-9_]+)|([1-9][0-9_]*))(\.[0-9_]+)?([eE](\+|-)?[0-9_]+)?)')),
    TokenSpec(tokens.TYPE_BOOLEAN, re.compile(r'^(true|false)')),
    TokenSpec(tokens.TYPE_OP_SQUARE_LEFT_BRACKET, re.compile(r'^(\[)')),
    TokenSpec(tokens.TYPE_OP_SQUARE_RIGHT_BRACKET, re.compile(r'^(\])')),
    TokenSpec(tokens.TYPE_OP_CURLY_LEFT_BRACKET, re.compile(r'^(\{)')),
    TokenSpec(tokens.TYPE_OP_CURLY_RIGHT_BRACKET, re.compile(r'^(\})')),
    TokenSpec(tokens.TYPE_OP_ASSIGNMENT, re.compile(r'^(=)')),
    TokenSpec(tokens.TYPE_OP_COMMA, re.compile(r'^(,)')),
    TokenSpec(tokens.TYPE_OP_DOUBLE_SQUARE_LEFT_BRACKET, re.compile(r'^(\[\[)')),
    TokenSpec(tokens.TYPE_OP_DOUBLE_SQUARE_RIGHT_BRACKET, re.compile(r'^(\]\])')),
    TokenSpec(tokens.TYPE_OPT_DOT, re.compile(r'^(\.)')),
    TokenSpec(tokens.TYPE_NEWLINE, re.compile('^(\n|\r\n)')),
)


def _next_token_candidates(source):
    matches = []
    for token_spec in _LEXICAL_SPECS:
        match = token_spec.re.search(source)
        if match:
            matches.append(tokens.Token(token_spec.type, match.group(1)))
    return matches


def _choose_from_next_token_candidates(candidates):

    if len(candidates) == 1:
        return candidates[0]
    elif len(candidates) > 1:
        # Return the maximal-munch with ties broken by natural order of token type.
        maximal_munch_length = max(len(token.source_substring) for token in candidates)
        maximal_munches = [token for token in candidates if len(token.source_substring) == maximal_munch_length]
        return sorted(maximal_munches)[0]   # Return the first in sorting by priority


def _munch_a_token(source):
    """
    Munches a single Token instance if it could recognize one at the beginning of the
    given source text, or None if no token type could be recognized.
    """
    candidates = _next_token_candidates(source)
    return _choose_from_next_token_candidates(candidates)


class LexerError(TOMLError):

    def __init__(self, message):
        self._message = message

    def __repr__(self):
        return self._message

    def __str__(self):
        return self._message


def tokenize(source, is_top_level=False):
    """
    Tokenizes the input TOML source into a stream of tokens.

    If is_top_level is set to True, will make sure that the input source has a trailing newline character
    before it is tokenized.

    Raises a LexerError when it fails recognize another token while not at the end of the source.
    """

    # Newlines are going to be normalized to UNIX newlines.
    source = source.replace('\r\n', '\n')

    if is_top_level and source and source[-1] != '\n':
        source += '\n'

    next_row = 1
    next_col = 1
    next_index = 0

    while next_index < len(source):

        new_token = _munch_a_token(source[next_index:])

        if not new_token:
            raise LexerError("failed to read the next token at ({}, {}): {}".format(
                next_row, next_col, source[next_index:]))

        # Set the col and row on the new token
        new_token = tokens.Token(new_token.type, new_token.source_substring, next_col, next_row)

        # Advance the index, row and col count
        next_index += len(new_token.source_substring)
        for c in new_token.source_substring:
            if c == '\n':
                next_row += 1
                next_col = 1
            else:
                next_col += 1

        yield new_token

