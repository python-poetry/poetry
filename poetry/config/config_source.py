from typing import Any


class ConfigSource(object):
    def add_property(self, key: str, value: Any) -> None:
        raise NotImplementedError()

    def remove_property(self, key: str) -> None:
        raise NotImplementedError()
