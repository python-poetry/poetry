from typing import TYPE_CHECKING
from typing import Dict
from typing import Optional

from tests.compat import Protocol


if TYPE_CHECKING:
    from pathlib import Path

    from cleo.io.io import IO
    from cleo.testers.command_tester import CommandTester

    from poetry.config.config import Config
    from poetry.config.source import Source
    from poetry.installation import Installer
    from poetry.installation.executor import Executor
    from poetry.poetry import Poetry
    from poetry.utils.env import Env


class CommandTesterFactory(Protocol):
    def __call__(
        self,
        command: str,
        poetry: Optional["Poetry"] = None,
        installer: Optional["Installer"] = None,
        executor: Optional["Executor"] = None,
        environment: Optional["Env"] = None,
    ) -> "CommandTester":
        ...


class SourcesFactory(Protocol):
    def __call__(
        self, poetry: "Poetry", sources: "Source", config: "Config", io: "IO"
    ) -> None:
        ...


class ProjectFactory(Protocol):
    def __call__(
        self,
        name: Optional[str] = None,
        dependencies: Optional[Dict[str, str]] = None,
        dev_dependencies: Optional[Dict[str, str]] = None,
        pyproject_content: Optional[str] = None,
        poetry_lock_content: Optional[str] = None,
        install_deps: bool = True,
    ) -> "Poetry":
        ...


class FixtureDirGetter(Protocol):
    def __call__(self, name: str) -> "Path":
        ...
