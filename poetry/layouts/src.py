from pathlib import Path

from .layout import Layout


class SrcLayout(Layout):
    @property
    def basedir(self) -> "Path":
        return Path("src")
