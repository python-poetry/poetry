"""
LFU cache Written by Shane Wang
https://medium.com/@epicshane/a-python-implementation-of-lfu-least-frequently-used-cache-with-o-1-time-complexity-e16b34a3c49b
https://github.com/luxigner/lfu_cache
Modified by Sep Dehpour
"""
from collections import defaultdict
from threading import Lock
from statistics import mean
from deepdiff.helper import not_found, dict_, SetOrdered


class CacheNode:
    def __init__(self, key, report_type, value, freq_node, pre, nxt):
        self.key = key
        if report_type:
            self.content = defaultdict(SetOrdered)
            self.content[report_type].add(value)
        else:
            self.content = value
        self.freq_node = freq_node
        self.pre = pre  # previous CacheNode
        self.nxt = nxt  # next CacheNode

    def free_myself(self):
        if self.freq_node.cache_head == self.freq_node.cache_tail:  # type: ignore
            self.freq_node.cache_head = self.freq_node.cache_tail = None  # type: ignore
        elif self.freq_node.cache_head == self:  # type: ignore
            self.nxt.pre = None  # type: ignore
            self.freq_node.cache_head = self.nxt  # type: ignore
        elif self.freq_node.cache_tail == self:  # type: ignore
            self.pre.nxt = None  # type: ignore
            self.freq_node.cache_tail = self.pre  # type: ignore
        else:
            self.pre.nxt = self.nxt  # type: ignore
            self.nxt.pre = self.pre  # type: ignore

        self.pre = None
        self.nxt = None
        self.freq_node = None


class FreqNode:
    def __init__(self, freq, pre, nxt):
        self.freq = freq
        self.pre = pre  # previous FreqNode
        self.nxt = nxt  # next FreqNode
        self.cache_head = None  # CacheNode head under this FreqNode
        self.cache_tail = None  # CacheNode tail under this FreqNode

    def count_caches(self):
        if self.cache_head is None and self.cache_tail is None:
            return 0
        elif self.cache_head == self.cache_tail:
            return 1
        else:
            return '2+'

    def remove(self):
        if self.pre is not None:
            self.pre.nxt = self.nxt
        if self.nxt is not None:
            self.nxt.pre = self.pre

        pre = self.pre
        nxt = self.nxt
        self.pre = self.nxt = self.cache_head = self.cache_tail = None

        return (pre, nxt)

    def pop_head_cache(self):
        if self.cache_head is None and self.cache_tail is None:
            return None
        elif self.cache_head == self.cache_tail:
            cache_head = self.cache_head
            self.cache_head = self.cache_tail = None
            return cache_head
        else:
            cache_head = self.cache_head
            self.cache_head.nxt.pre = None  # type: ignore
            self.cache_head = self.cache_head.nxt  # type: ignore
            return cache_head

    def append_cache_to_tail(self, cache_node):
        cache_node.freq_node = self

        if self.cache_head is None and self.cache_tail is None:
            self.cache_head = self.cache_tail = cache_node
        else:
            cache_node.pre = self.cache_tail
            cache_node.nxt = None
            self.cache_tail.nxt = cache_node  # type: ignore
            self.cache_tail = cache_node

    def insert_after_me(self, freq_node):
        freq_node.pre = self
        freq_node.nxt = self.nxt

        if self.nxt is not None:
            self.nxt.pre = freq_node

        self.nxt = freq_node

    def insert_before_me(self, freq_node):
        if self.pre is not None:
            self.pre.nxt = freq_node

        freq_node.pre = self.pre
        freq_node.nxt = self
        self.pre = freq_node


class LFUCache:

    def __init__(self, capacity):
        self.cache = dict_()  # {key: cache_node}
        if capacity <= 0:
            raise ValueError('Capacity of LFUCache needs to be positive.')  # pragma: no cover.
        self.capacity = capacity
        self.freq_link_head = None
        self.lock = Lock()

    def get(self, key):
        with self.lock:
            if key in self.cache:
                cache_node = self.cache[key]
                freq_node = cache_node.freq_node
                content = cache_node.content

                self.move_forward(cache_node, freq_node)

                return content
            else:
                return not_found

    def set(self, key, report_type=None, value=None):
        with self.lock:
            if key in self.cache:
                cache_node = self.cache[key]
                if report_type:
                    cache_node.content[report_type].add(value)
                else:
                    cache_node.content = value
            else:
                if len(self.cache) >= self.capacity:
                    self.dump_cache()

                self.create_cache_node(key, report_type, value)

    def __contains__(self, key):
        return key in self.cache

    def move_forward(self, cache_node, freq_node):
        if freq_node.nxt is None or freq_node.nxt.freq != freq_node.freq + 1:
            target_freq_node = FreqNode(freq_node.freq + 1, None, None)
            target_empty = True
        else:
            target_freq_node = freq_node.nxt
            target_empty = False

        cache_node.free_myself()
        target_freq_node.append_cache_to_tail(cache_node)

        if target_empty:
            freq_node.insert_after_me(target_freq_node)

        if freq_node.count_caches() == 0:
            if self.freq_link_head == freq_node:
                self.freq_link_head = target_freq_node

            freq_node.remove()

    def dump_cache(self):
        head_freq_node = self.freq_link_head
        self.cache.pop(head_freq_node.cache_head.key)  # type: ignore
        head_freq_node.pop_head_cache()  # type: ignore

        if head_freq_node.count_caches() == 0:  # type: ignore
            self.freq_link_head = head_freq_node.nxt  # type: ignore
            head_freq_node.remove()  # type: ignore

    def create_cache_node(self, key, report_type, value):
        cache_node = CacheNode(
            key=key, report_type=report_type,
            value=value, freq_node=None, pre=None, nxt=None)
        self.cache[key] = cache_node

        if self.freq_link_head is None or self.freq_link_head.freq != 0:
            new_freq_node = FreqNode(0, None, None)
            new_freq_node.append_cache_to_tail(cache_node)

            if self.freq_link_head is not None:
                self.freq_link_head.insert_before_me(new_freq_node)

            self.freq_link_head = new_freq_node
        else:
            self.freq_link_head.append_cache_to_tail(cache_node)

    def get_sorted_cache_keys(self):
        result = [(i, freq.freq_node.freq) for i, freq in self.cache.items()]
        result.sort(key=lambda x: -x[1])
        return result

    def get_average_frequency(self):
        return mean(freq.freq_node.freq for freq in self.cache.values())


class DummyLFU:

    def __init__(self, *args, **kwargs):
        pass

    set = __init__
    get = __init__

    def __contains__(self, key):
        return False
