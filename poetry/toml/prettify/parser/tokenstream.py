class TokenStream:
    """
    An immutable subset of a token sequence
    """

    class EndOfStream(Exception):
        pass

    Nothing = tuple()

    def __init__(self, _tokens, offset=0):
        if isinstance(_tokens, tuple):
            self._tokens = _tokens
        else:
            self._tokens = tuple(_tokens)
        self._head_index = offset

    def __len__(self):
        return len(self._tokens) - self.offset

    @property
    def head(self):
        try:
            return self._tokens[self._head_index]
        except IndexError:
            raise TokenStream.EndOfStream

    @property
    def tail(self):
        return TokenStream(self._tokens, offset=self._head_index+1)

    @property
    def offset(self):
        return self._head_index

    @property
    def at_end(self):
        return self.offset >= len(self._tokens)
