from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Protocol


if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from typing import ContextManager
    from typing import Dict
    from typing import Tuple

    from cleo.io.io import IO
    from cleo.testers.command_tester import CommandTester
    from httpretty.core import HTTPrettyRequest
    from packaging.utils import NormalizedName

    from poetry.config.config import Config
    from poetry.config.source import Source
    from poetry.installation import Installer
    from poetry.installation.executor import Executor
    from poetry.poetry import Poetry
    from poetry.repositories.legacy_repository import LegacyRepository
    from poetry.utils.env import Env
    from tests.repositories.fixtures.distribution_hashes import DistributionHash

    HTTPrettyResponse = Tuple[int, Dict[str, Any], bytes]  # status code, headers, body
    HTTPrettyRequestCallback = Callable[
        [HTTPrettyRequest, str, Dict[str, Any]], HTTPrettyResponse
    ]
    HTTPPrettyRequestCallbackWrapper = Callable[
        [HTTPrettyRequestCallback], HTTPrettyRequestCallback
    ]


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


class NormalizedNameTransformer(Protocol):
    def __call__(self, name: str) -> NormalizedName: ...


class SpecializedLegacyRepositoryMocker(Protocol):
    def __call__(
        self,
        transformer_or_suffix: NormalizedNameTransformer | str,
        repository_name: str = "special",
        repository_url: str = "https://legacy.foo.bar",
    ) -> LegacyRepository: ...


class PythonHostedFileMocker(Protocol):
    def __call__(
        self,
        distribution_locations: list[Path],
        metadata_locations: list[Path],
    ) -> None: ...


class PackageDistributionLookup(Protocol):
    def __call__(self, name: str) -> Path | None: ...


class DistributionHashGetter(Protocol):
    def __call__(self, name: str) -> DistributionHash: ...


class SetProjectContext(Protocol):
    def __call__(
        self, project: str | Path, in_place: bool = False
    ) -> ContextManager[Path]: ...
