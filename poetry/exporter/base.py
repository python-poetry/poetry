from abc import abstractmethod
from pathlib import Path
from typing import Any
from typing import Union

from clikit.api.io import IO

from poetry.poetry import Poetry
from poetry.utils._compat import decode


class Exporter:
    def __init__(self, poetry):  # type: (Poetry) -> None
        self._poetry = poetry

    @staticmethod
    def _output(content, cwd, output):  # type: (str, Path, Union[IO, str]) -> None
        decoded = decode(content)
        try:
            output.write(decoded)
        except AttributeError:
            filepath = cwd / output
            with filepath.open("w", encoding="utf-8") as f:
                f.write(decoded)

    @abstractmethod
    def _export(self, *args, **kwargs):  # type: (*Any, **Any) -> str
        raise NotImplementedError()

    def export(
        self, cwd, output, **kwargs
    ):  # type: (Path, Union[IO, Path, str], **Any) -> None
        content = self._export(**kwargs)
        self._output(content, cwd, output)
