from ..tokens import py2toml, toml2py
from ..util import is_dict_like, is_sequence_like
from . import common
from .errors import InvalidElementError


class AtomicElement(common.TokenElement):
    """
    An element containing a sequence of tokens representing a single atomic value that can be updated in place.

    Raises:
        InvalidElementError: when passed an invalid sequence of tokens.
    """

    def __init__(self, _tokens):
        common.TokenElement.__init__(self, _tokens, common.TYPE_ATOMIC)

    def _validate_tokens(self, _tokens):
        if len([token for token in _tokens if not token.type.is_metadata]) != 1:
            raise InvalidElementError('Tokens making up an AtomicElement must contain only one non-metadata token')

    def serialized(self):
        return ''.join(token.source_substring for token in self.tokens)

    def _value_token_index(self):
        """
        Finds the token where the value is stored.
        """
        # TODO: memoize this value
        for i, token in enumerate(self.tokens):
            if not token.type.is_metadata:
                return i
        raise RuntimeError('could not find a value token')

    @property
    def value(self):
        """
        Returns a Python value contained in this atomic element.
        """
        return toml2py.deserialize(self._tokens[self._value_token_index()])

    @property
    def primitive_value(self):
        return self.value

    def set(self, value):
        """
        Sets the contained value to the given one.
        """
        assert (not is_sequence_like(value)) and (not is_dict_like(value)), 'the value must be an atomic primitive'
        token_index = self._value_token_index()
        self._tokens[token_index] = py2toml.create_primitive_token(value)
