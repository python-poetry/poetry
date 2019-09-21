from typing import Any


class ConfigSource(object):
    def add_property(self, key, value):  # type: (str, Any) -> None
        raise NotImplementedError()

    def remove_property(self, key):  # type: (str) -> None
        raise NotImplementedError()
