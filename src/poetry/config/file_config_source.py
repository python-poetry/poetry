from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING
from typing import Any

from tomlkit import document
from tomlkit import table

from poetry.config.config_source import ConfigSource
from poetry.config.config_source import PropertyNotFoundError
from poetry.config.config_source import split_key


if TYPE_CHECKING:
    from collections.abc import Iterator
    from collections.abc import Sequence

    from tomlkit.toml_document import TOMLDocument

    from poetry.toml.file import TOMLFile


class FileConfigSource(ConfigSource):
    def __init__(self, file: TOMLFile) -> None:
        self._file = file

    @property
    def name(self) -> str:
        return str(self._file.path)

    @property
    def file(self) -> TOMLFile:
        return self._file

    def get_property(self, key: str | Sequence[str]) -> Any:
        keys = split_key(key)

        config = self.file.read() if self.file.exists() else {}

        for i, sub_key in enumerate(keys):
            if sub_key not in config:
                raise PropertyNotFoundError(f"Key {'.'.join(keys)} not in config")

            if i == len(keys) - 1:
                return config[sub_key]

            config = config[sub_key]

    def add_property(self, key: str | Sequence[str], value: Any) -> None:
        with self.secure() as toml:
            config: dict[str, Any] = toml
            keys = split_key(key)

            for i, sub_key in enumerate(keys):
                if sub_key not in config and i < len(keys) - 1:
                    config[sub_key] = table()

                if i == len(keys) - 1:
                    config[sub_key] = value
                    break

                config = config[sub_key]

    def remove_property(self, key: str | Sequence[str]) -> None:
        with self.secure() as toml:
            config: dict[str, Any] = toml
            keys = split_key(key)

            # Descend to the leaf, recording the (parent, key) at each step.
            stack = []
            current = config
            for key in keys:
                if key not in current:
                    return
                stack.append((current, key))
                current = current[key]

            # Delete the leaf, then walk back up pruning any now-empty parents.
            while stack:
                parent, key = stack.pop()
                del parent[key]
                if parent:
                    break

    @contextmanager
    def secure(self) -> Iterator[TOMLDocument]:
        if self.file.exists():
            initial_config = self.file.read()
            config = self.file.read()
        else:
            initial_config = document()
            config = document()

        new_file = not self.file.exists()

        yield config

        try:
            # Ensuring the file is only readable and writable
            # by the current user
            mode = 0o600

            if new_file:
                self.file.path.touch(mode=mode)

            self.file.write(config)
        except Exception:
            self.file.write(initial_config)

            raise
