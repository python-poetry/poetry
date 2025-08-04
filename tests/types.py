from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Protocol


if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager
    from pathlib import Path

    from cleo.io.inputs.argument import Argument
    from cleo.io.inputs.option import Option
    from cleo.io.io import IO
    from cleo.testers.command_tester import CommandTester
    from httpretty.core import HTTPrettyRequest
    from packaging.utils import NormalizedName
    from poetry.core.packages.dependency import Dependency
    from poetry.core.packages.package import Package

    from poetry.config.config import Config
    from poetry.config.source import Source
    from poetry.console.commands.command import Command
    from poetry.installation import Installer
    from poetry.installation.executor import Executor
    from poetry.poetry import Poetry
    from poetry.repositories.legacy_repository import LegacyRepository
    from poetry.utils.env import Env
    from poetry.utils.env.python import Python
    from tests.repositories.fixtures.distribution_hashes import DistributionHash

    HTTPrettyResponse = tuple[int, dict[str, Any], bytes]  # status code, headers, body
    HTTPrettyRequestCallback = Callable[
        [HTTPrettyRequest, str, dict[str, Any]], HTTPrettyResponse
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


class PackageFactory(Protocol):
    def __call__(
        self,
        name: str,
        version: str | None = None,
        dependencies: list[Dependency] | None = None,
        extras: dict[str, list[str]] | None = None,
        merge_extras: bool = False,
    ) -> Package: ...


class CommandFactory(Protocol):
    def __call__(
        self,
        command_name: str,
        command_arguments: list[Argument] | None = None,
        command_options: list[Option] | None = None,
        command_description: str = "",
        command_help: str = "",
        command_handler: Callable[[Command], int] | str | None = None,
    ) -> Command: ...


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
    ) -> AbstractContextManager[Path]: ...


class MockedPythonRegister(Protocol):
    def __call__(
        self,
        version: str,
        executable_name: str | Path | None = None,
        implementation: str | None = None,
        parent: str | Path | None = None,
        make_system: bool = False,
    ) -> Python: ...


class MockedPoetryPythonRegister(Protocol):
    def __call__(
        self,
        version: str,
        implementation: str,
        with_install_dir: bool = False,
    ) -> Path: ...
