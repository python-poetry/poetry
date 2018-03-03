from .. import tokens
from ..tokens import toml2py
from . import common
from .common import TokenElement
from .errors import InvalidElementError

_opening_bracket_types = (tokens.TYPE_OP_SQUARE_LEFT_BRACKET, tokens.TYPE_OP_DOUBLE_SQUARE_LEFT_BRACKET)
_closing_bracket_types = (tokens.TYPE_OP_SQUARE_RIGHT_BRACKET, tokens.TYPE_OP_DOUBLE_SQUARE_RIGHT_BRACKET)
_name_types = (
    tokens.TYPE_BARE_STRING,
    tokens.TYPE_LITERAL_STRING,
    tokens.TYPE_STRING,
)


class TableHeaderElement(TokenElement):
    """
    An element containing opening and closing single and double square brackets, strings and dots and ending with
    a newline.
    
    Raises InvalidElementError.
    """
    
    def __init__(self, _tokens):
        TokenElement.__init__(self, _tokens, common.TYPE_MARKUP)
        self._names = tuple(toml2py.deserialize(token) for token in self._tokens if token.type in _name_types)

    @property
    def is_array_of_tables(self):
        opening_bracket = next(token for i, token in enumerate(self._tokens) if token.type in _opening_bracket_types)
        return opening_bracket.type == tokens.TYPE_OP_DOUBLE_SQUARE_LEFT_BRACKET

    @property
    def names(self):
        """
        Returns a sequence of string names making up this table header name.
        """
        return self._names

    def has_name_prefix(self, names):
        """
        Returns True if the header names is prefixed by the given sequence of names.
        """
        for i, name in enumerate(names):
            if self.names[i] != name:
                return False
        return True

    def serialized(self):
        return ''.join(token.source_substring for token in self._tokens)

    def is_named(self, names):
        """
        Returns True if the given name sequence matches the full name of this header.
        """
        return tuple(names) == self.names

    def _validate_tokens(self, _tokens):

        opening_bracket_i = next((i for i, token in enumerate(_tokens)
                                  if token.type in _opening_bracket_types), float('-inf'))

        if opening_bracket_i < 0:
            raise InvalidElementError('Expected an opening bracket')

        _tokens = _tokens[opening_bracket_i+1:]
        first_name_i = next((i for i, token in enumerate(_tokens) if token.type in _name_types), float('-inf'))
        if first_name_i < 0:
            raise InvalidElementError('Expected a table header name')

        _tokens = _tokens[first_name_i+1:]

        while True:

            next_dot_i = next((i for i, token in enumerate(_tokens) if token.type == tokens.TYPE_OPT_DOT),
                              float('-inf'))
            if next_dot_i < 0:
                break

            _tokens = _tokens[next_dot_i+1:]

            next_name_i = next((i for i, token in enumerate(_tokens) if token.type in _name_types), float('-inf'))
            if next_name_i < 0:
                raise InvalidElementError('Expected a name after the dot')

            _tokens = _tokens[next_name_i+1:]

        closing_bracket_i = next((i for i, token in enumerate(_tokens) if token.type in _closing_bracket_types),
                                 float('-inf'))

        if closing_bracket_i < 0:
            raise InvalidElementError('Expected a closing bracket')

        if _tokens[-1].type != tokens.TYPE_NEWLINE:
            raise InvalidElementError('Must end with a newline')
