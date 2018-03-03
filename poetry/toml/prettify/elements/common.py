from abc import abstractmethod

TYPE_METADATA = 'element-metadata'
TYPE_ATOMIC = 'element-atomic'
TYPE_CONTAINER = 'element-container'
TYPE_MARKUP = 'element-markup'


class Element:
    """
    An Element:
        - is one or more Token instances, or one or more other Element instances. Not both.
        - knows how to serialize its value back to valid TOML code.

    A non-metadata Element is an Element that:
        - knows how to deserialize its content into usable Python primitive, seq-like,  or dict-like value.
        - knows how to update its content from a Python primitive, seq-like, or dict-like value
            while maintaining its formatting.
    """

    def __init__(self, _type):
        self._type = _type

    @property
    def type(self):
        return self._type

    @abstractmethod
    def serialized(self):
        """
        TOML serialization of this element as str.
        """
        raise NotImplementedError


class TokenElement(Element):
    """
    An Element made up of tokens
    """

    def __init__(self, _tokens, _type):
        Element.__init__(self, _type)
        self._validate_tokens(_tokens)
        self._tokens = list(_tokens)

    @property
    def tokens(self):
        return self._tokens

    @property
    def first_token(self):
        return self._tokens[0]

    @abstractmethod
    def _validate_tokens(self, _tokens):
        raise NotImplementedError

    def serialized(self):
        return ''.join(token.source_substring for token in self._tokens)

    def __repr__(self):
        return repr(self.tokens)

    @property
    def primitive_value(self):
        """
        Returns a primitive Python value without any formatting or markup metadata.
        """
        raise NotImplementedError


class ContainerElement(Element):
    """
    An Element containing exclusively other elements.
    """

    def __init__(self, sub_elements):
        Element.__init__(self, TYPE_CONTAINER)
        self._sub_elements = list(sub_elements)

    @property
    def sub_elements(self):
        return self._sub_elements

    @property
    def elements(self):
        return self.sub_elements

    def serialized(self):
        return ''.join(element.serialized() for element in self.sub_elements)

    def __eq__(self, other):
        return self.primitive_value == other

    def __repr__(self):
        return repr(self.primitive_value)

    @property
    def primitive_value(self):
        """
        Returns a primitive Python value without any formatting or markup metadata.
        """
        raise NotImplementedError


