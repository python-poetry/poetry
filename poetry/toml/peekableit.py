import itertools


class PeekableIterator:

    # Returned by peek() when the iterator is exhausted. Truthiness is False.
    Nothing = tuple()

    def __init__(self, iter):
        self._iter = iter

    def __next__(self):
        return next(self._iter)

    def next(self):
        return self.__next__()

    def __iter__(self):
        return self

    def peek(self):
        """
        Returns PeekableIterator.Nothing when the iterator is exhausted.
        """
        try:
            v = next(self._iter)
            self._iter = itertools.chain((v,), self._iter)
            return v
        except StopIteration:
            return PeekableIterator.Nothing
