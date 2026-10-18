from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from build import ProjectBuilder
from cleo.io.buffered_io import BufferedIO
from dulwich import porcelain
from dulwich.repo import Repo
from poetry.core.packages.package import Package

from poetry.installation.executor import Executor
from poetry.installation.operations import Install
from poetry.installation.operations import Uninstall
from poetry.installation.operations import Update
from poetry.puzzle.transaction import Transaction
from poetry.repositories.installed_repository import InstalledRepository


if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_mock import MockerFixture

    from poetry.config.config import Config
    from poetry.repositories import RepositoryPool
    from poetry.utils.env import VirtualEnv


pytestmark = pytest.mark.skip_git_mock


@pytest.fixture
def git_package(tmp_path: Path) -> Callable[..., Package]:
    def create(
        name: str,
        *,
        owner: str = "owner",
        subdirectory: str = "",
        value: str | None = None,
    ) -> Package:
        root = tmp_path / owner / "repository"
        root.mkdir(parents=True, exist_ok=True)
        if not (root / ".git").exists():
            Repo.init(str(root)).close()
        project = root / subdirectory
        project.mkdir(parents=True, exist_ok=True)
        (project / "pyproject.toml").write_text(
            f'[project]\nname = "{name}"\nversion = "1.0"\n'
            '[build-system]\nrequires = ["poetry-core"]\n'
            'build-backend = "poetry.core.masonry.api"\n',
            encoding="utf-8",
        )
        module = project / name
        module.mkdir(exist_ok=True)
        (module / "__init__.py").write_text(
            f'VALUE = "{value or name}"\n', encoding="utf-8"
        )
        porcelain.add(str(root))
        revision = porcelain.commit(
            str(root), message=name.encode(), author=b"Aarav <aaravsjadav@gmail.com>"
        ).decode()
        return Package(
            name,
            "1.0",
            source_type="git",
            source_url=f"file://localhost{root.as_posix()}",
            source_reference=revision,
            source_resolved_reference=revision,
            source_subdirectory=subdirectory or None,
            develop=True,
        )

    return create


@pytest.fixture
def executor(
    tmp_venv: VirtualEnv,
    pool: RepositoryPool,
    config: Config,
    tmp_path: Path,
    mocker: MockerFixture,
) -> Executor:
    instance = Executor(tmp_venv, pool, config, BufferedIO())

    def prepare(path: Path, **kwargs: object) -> Path:
        return Path(ProjectBuilder(path).build("editable", tmp_path / "wheels"))

    mocker.patch.object(instance._chef, "prepare", side_effect=prepare)
    return instance


def test_same_basename_editable_repositories(
    git_package: Callable[..., Package], executor: Executor, tmp_venv: VirtualEnv
) -> None:
    first = git_package("first", owner="one")
    second = git_package("second", owner="two")
    requested = [first.clone(), second.clone()]
    assert executor.execute([Install(first), Install(second)]) == 0
    operations = Transaction(
        [], requested, InstalledRepository.load(tmp_venv).packages
    ).calculate_operations()
    assert all(operation.skipped for operation in operations)
    assert (
        tmp_venv.run(
            "python", "-c", "import first, second; print(first.VALUE, second.VALUE)"
        ).strip()
        == "first second"
    )
    paths = [_installed_path(tmp_venv, name) for name in ("first", "second")]
    assert paths[0] != paths[1]
    assert all(path.exists() for path in paths)


def test_editable_monorepo_different_revisions(
    git_package: Callable[..., Package],
    executor: Executor,
    tmp_venv: VirtualEnv,
    tmp_path: Path,
) -> None:
    first = git_package("first", subdirectory="one")
    source = tmp_path / "owner/repository"
    (source / "one/first/__init__.py").write_text(
        'VALUE = "changed"\n', encoding="utf-8"
    )
    second = git_package("second", subdirectory="two")
    requested = [first.clone(), second.clone()]
    assert executor.execute([Install(first), Install(second)]) == 0
    operations = Transaction(
        [], requested, InstalledRepository.load(tmp_venv).packages
    ).calculate_operations()
    assert all(operation.skipped for operation in operations)
    assert (
        tmp_venv.run(
            "python", "-c", "import first, second; print(first.VALUE, second.VALUE)"
        ).strip()
        == "first second"
    )


def _installed_path(env: VirtualEnv, name: str) -> Path:
    paths = InstalledRepository.get_package_paths(env, name)
    assert len(paths) == 1
    return paths.pop()


def _installed_source(env: VirtualEnv, name: str) -> Package:
    return next(
        package
        for package in InstalledRepository.load(env).packages
        if package.name == name
    )


def test_reinstall_preserves_checkout_and_edits(
    git_package: Callable[..., Package], executor: Executor, tmp_venv: VirtualEnv
) -> None:
    first = git_package("first")
    repeat = first.clone()
    same_revision = first.clone()
    assert executor.execute([Install(first)]) == 0
    source = _installed_path(tmp_venv, "first")
    module = source / "first/__init__.py"
    module.write_text('VALUE = "local edit"\n', encoding="utf-8")
    assert executor.execute([Install(repeat)]) == 0
    assert _installed_path(tmp_venv, "first") == source
    assert module.read_text(encoding="utf-8") == 'VALUE = "local edit"\n'
    assert (
        executor.execute([Update(_installed_source(tmp_venv, "first"), same_revision)])
        == 0
    )
    assert module.exists()


def test_update_removes_old_owned_checkout_after_install(
    git_package: Callable[..., Package], executor: Executor, tmp_venv: VirtualEnv
) -> None:
    first = git_package("first")
    assert executor.execute([Install(first)]) == 0
    installed = _installed_source(tmp_venv, "first")
    old_source = _installed_path(tmp_venv, "first")
    updated = git_package("first", value="updated")
    assert executor.execute([Update(installed, updated)]) == 0
    assert not old_source.exists()
    assert (
        tmp_venv.run("python", "-c", "import first; print(first.VALUE)").strip()
        == "updated"
    )
    assert _installed_path(tmp_venv, "first").exists()


@pytest.mark.parametrize("failure", ["build", "uninstall", "install"])
def test_failed_update_preserves_old_source(
    git_package: Callable[..., Package],
    executor: Executor,
    tmp_venv: VirtualEnv,
    mocker: MockerFixture,
    failure: str,
) -> None:
    assert executor.execute([Install(git_package("first"))]) == 0
    source = _installed_path(tmp_venv, "first")
    installed = _installed_source(tmp_venv, "first")
    updated = git_package("first", value="updated")
    pending = executor._git_source.path_for(updated)
    target = {
        "build": (executor._chef, "prepare"),
        "uninstall": (executor, "_remove"),
        "install": (executor._wheel_installer, "install"),
    }[failure]
    mocker.patch.object(*target, side_effect=RuntimeError("failed update"))
    assert executor.execute([Update(installed, updated)]) == 1
    assert (source / "first/__init__.py").read_text(
        encoding="utf-8"
    ) == 'VALUE = "first"\n'
    assert not pending.exists()
    if failure != "install":
        assert (
            tmp_venv.run("python", "-c", "import first; print(first.VALUE)").strip()
            == "first"
        )


def test_uninstall_keeps_other_editable_sources(
    git_package: Callable[..., Package], executor: Executor, tmp_venv: VirtualEnv
) -> None:
    assert (
        executor.execute(
            [
                Install(git_package("first", subdirectory="one")),
                Install(git_package("second", subdirectory="two")),
            ]
        )
        == 0
    )
    first = _installed_source(tmp_venv, "first")
    source = _installed_path(tmp_venv, "first")
    assert source.name == "one"
    assert executor.execute([Uninstall(first)]) == 0
    assert not source.exists()
    assert _installed_path(tmp_venv, "second").exists()
    assert (
        tmp_venv.run("python", "-c", "import second; print(second.VALUE)").strip()
        == "second"
    )


def test_absolute_local_git_origin_cleanup(
    git_package: Callable[..., Package],
    executor: Executor,
    tmp_venv: VirtualEnv,
    tmp_path: Path,
) -> None:
    package = git_package("first")
    package._source_url = str(tmp_path / "owner/repository")
    assert executor.execute([Install(package)]) == 0
    installed = _installed_source(tmp_venv, "first")
    checkout = _installed_path(tmp_venv, "first")
    assert installed.source_url == str(tmp_path / "owner/repository")
    assert executor.execute([Uninstall(installed)]) == 0
    assert not checkout.exists()
    assert (tmp_path / "owner/repository").exists()
