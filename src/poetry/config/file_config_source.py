from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING
from typing import Any

from tomlrt import Document

from poetry.config.config_source import ConfigSource
from poetry.config.config_source import PropertyNotFoundError
from poetry.config.config_source import split_key


if TYPE_CHECKING:
    from collections.abc import Iterator
    from collections.abc import Sequence

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
        config = self.file.read() if self.file.exists() else Document()
        try:
            return config.entry(key)
        except KeyError:
            keys = split_key(key)
            raise PropertyNotFoundError(f"Key {'.'.join(keys)} not in config")

    def add_property(self, key: str | Sequence[str], value: Any) -> None:
        with self.secure() as config:
            config.install(key, value)

    def remove_property(self, key: str | Sequence[str]) -> None:
        with self.secure() as config:
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
    def secure(self) -> Iterator[Document]:
        if self.file.exists():
            initial_config = self.file.read()
            config = self.file.read()
        else:
            initial_config = Document()
            config = Document()

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
