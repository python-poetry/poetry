from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Protocol


if TYPE_CHECKING:
    from pathlib import Path

    import requests

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
        poetry: Poetry | None = None,
        installer: Installer | None = None,
        executor: Executor | None = None,
        environment: Env | None = None,
    ) -> CommandTester: ...


class SourcesFactory(Protocol):
    def __call__(
        self, poetry: Poetry, sources: Source, config: Config, io: IO
    ) -> None: ...


class ProjectFactory(Protocol):
    def __call__(
        self,
        name: str | None = None,
        dependencies: dict[str, str] | None = None,
        dev_dependencies: dict[str, str] | None = None,
        pyproject_content: str | None = None,
        poetry_lock_content: str | None = None,
        install_deps: bool = True,
        source: Path | None = None,
        locker_config: dict[str, Any] | None = None,
        use_test_locker: bool = True,
    ) -> Poetry: ...


class FixtureDirGetter(Protocol):
    def __call__(self, name: str) -> Path: ...


class FixtureCopier(Protocol):
    def __call__(self, relative_path: str, target: Path | None = None) -> Path: ...


class HTMLPageGetter(Protocol):
    def __call__(self, content: str, base_url: str | None = None) -> str: ...


class RequestsSessionGet(Protocol):
    def __call__(self, url: str, **__: Any) -> requests.Response: ...
