from typing import Any  # noqa: TC002


class ConfigSource:
    def add_property(self, key: str, value: Any) -> None:
        raise NotImplementedError()

    def remove_property(self, key: str) -> None:
        raise NotImplementedError()
