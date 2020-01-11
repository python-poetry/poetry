from typing import TYPE_CHECKING
from typing import Optional


if TYPE_CHECKING:
    from pathlib import Path
    from typing import Optional

    from clikit.api.io.io import IO

    from poetry.poetry import Poetry


class Bundler(object):
    @property
    def name(self) -> str:
        raise NotImplementedError()

    def bundle(
        self, poetry: "Poetry", io: "IO", path: "Path", executable: Optional[str] = None
    ) -> None:
        raise NotImplementedError()
