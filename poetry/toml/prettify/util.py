import itertools


def is_sequence_like(x):
    """
    Returns True if x exposes a sequence-like interface.
    """
    required_attrs = (
        '__len__',
        '__getitem__'
    )
    return all(hasattr(x, attr) for attr in required_attrs)


def is_dict_like(x):
    """
    Returns True if x exposes a dict-like interface.
    """
    required_attrs = (
        '__len__',
        '__getitem__',
        'keys',
        'values',
    )
    return all(hasattr(x, attr) for attr in required_attrs)


def join_with(iterable, separator):
    """
    Joins elements from iterable with separator and returns the produced sequence as a list.

    separator must be addable to a list.
    """
    inputs = list(iterable)
    b = []
    for i, element in enumerate(inputs):
        if isinstance(element, (list, tuple, set)):
            b += tuple(element)
        else:
            b += [element]
        if i < len(inputs)-1:
            b += separator
    return b


def chunkate_string(text, length):
    """
    Iterates over the given seq in chunks of at maximally the given length. Will never break a whole word.
    """
    iterator_index = 0

    def next_newline():
        try:
            return next(i for (i, c) in enumerate(text) if i > iterator_index and c == '\n')
        except StopIteration:
            return len(text)

    def next_breaker():
        try:
            return next(i for (i, c) in reversed(tuple(enumerate(text)))
                        if i >= iterator_index and
                        (i < iterator_index+length) and
                        c in (' ', '\t'))
        except StopIteration:
            return len(text)

    while iterator_index < len(text):
        next_chunk = text[iterator_index:min(next_newline(), next_breaker()+1)]
        iterator_index += len(next_chunk)
        yield next_chunk


def flatten_nested(nested_dicts):
    """
    Flattens dicts and sequences into one dict with tuples of keys representing the nested keys.

    Example
    >>> dd = { \
        'dict1': {'name': 'Jon', 'id': 42}, \
        'dict2': {'name': 'Sam', 'id': 41}, \
        'seq1': [{'one': 1, 'two': 2}] \
        }

    >>> flatten_nested(dd) == { \
        ('dict1', 'name'): 'Jon', ('dict1', 'id'): 42, \
        ('dict2', 'name'): 'Sam', ('dict2', 'id'): 41, \
        ('seq1', 0, 'one'): 1, ('seq1', 0, 'two'): 2, \
        }
    True
    """
    assert isinstance(nested_dicts, (dict, list, tuple)), 'Only works with a collection parameter'

    def items(c):
        if isinstance(c, dict):
            return c.items()
        elif isinstance(c, (list, tuple)):
            return enumerate(c)
        else:
            raise RuntimeError('c must be a collection')

    def flatten(dd):
        output = {}
        for k, v in items(dd):
            if isinstance(v, (dict, list, tuple)):
                for child_key, child_value in flatten(v).items():
                    output[(k,) + child_key] = child_value
            else:
                output[(k,)] = v
        return output

    return flatten(nested_dicts)


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
