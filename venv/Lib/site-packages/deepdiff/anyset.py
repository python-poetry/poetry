from deepdiff.deephash import DeepHash
from deepdiff.helper import dict_, SetOrdered


class AnySet:
    """
    Any object can be in this set whether hashable or not.
    Note that the current implementation has memory leak and keeps
    traces of objects in itself even after popping.
    However one the AnySet object is deleted, all those traces will be gone too.
    """
    def __init__(self, items=None):
        self._set = SetOrdered()
        self._hashes = dict_()
        self._hash_to_objects = dict_()
        if items:
            for item in items:
                self.add(item)

    def add(self, item):
        try:
            self._set.add(item)
        except TypeError:
            hashes_obj = DeepHash(item, hashes=self._hashes)
            hash_ = hashes_obj[item]
            if hash_ not in self._hash_to_objects:
                self._hash_to_objects[hash_] = item

    def __contains__(self, item):
        try:
            result = item in self._set
        except TypeError:
            hashes_obj = DeepHash(item, hashes=self._hashes)
            hash_ = hashes_obj[item]
            result = hash_ in self._hash_to_objects
        return result

    def pop(self):
        if self._set:
            return self._set.pop()
        else:
            return self._hash_to_objects.pop(next(iter(self._hash_to_objects)))

    def __eq__(self, other):
        set_part, hashes_to_objs_part = other
        return (self._set == set_part and self._hash_to_objects == hashes_to_objs_part)

    __req__ = __eq__

    def __repr__(self):
        return "< AnySet {}, {} >".format(self._set, self._hash_to_objects)

    __str__ = __repr__

    def __len__(self):
        return len(self._set) + len(self._hash_to_objects)

    def __iter__(self):
        for item in self._set:
            yield item
        for item in self._hash_to_objects.values():
            yield item

    def __bool__(self):
        return bool(self._set or self._hash_to_objects)
